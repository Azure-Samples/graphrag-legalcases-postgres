import argparse
import asyncio
import csv
import json
import logging
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from fastapi_app.postgres_engine import (
    create_postgres_engine_from_args,
    create_postgres_engine_from_env,
)

# Increase the field size limit
csv.field_size_limit(sys.maxsize)

logger = logging.getLogger("legalcaseapp")

BATCH_SIZE = 100


async def seed_data_from_csv(engine: AsyncEngine):
    csv_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "data/cases_summary.csv"))
    logger.info(f"Starting data seeding from {csv_file_path} using parameterized INSERT statements.")

    async with AsyncSession(engine) as session:
        batch = []
        try:
            with open(csv_file_path, encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    case_id = row["id"]
                    data = json.loads(row["data"])

                    description_vector_str = row["description_vector"]
                    description_vector = json.loads(description_vector_str)

                    summary = row["summary"]
                    summary_vector_str = row["summary_vector"]
                    summary_vector = json.loads(summary_vector_str)

                    # Add row to the batch
                    batch.append((case_id, json.dumps(data), description_vector, summary, summary_vector))

                    # When batch size is reached, insert into database
                    if len(batch) >= BATCH_SIZE:
                        await insert_batch(session, batch)
                        batch = []  # Clear the batch after inserting

                # Insert any remaining rows in the last batch
                if batch:
                    await insert_batch(session, batch)
                    batch = []

            logger.info("Data seeding completed successfully.")
        except Exception as e:
            logger.error(f"Data seeding failed: {e}")
            await session.rollback()
            return

        # Enable Apache AGE and set the search path
        await enable_age_extension(session)

        # # Insert cases as nodes in the graph
        await ingest_cases_to_graph_from_postgresql(session)

        # # Create edges based on citations
        await create_edges_from_citations(session)


async def insert_batch(session: AsyncSession, batch):
    """
    Insert a batch of rows into the database.
    """
    query = text("""
        INSERT INTO cases_summary (id, data, description_vector, summary, summary_vector)
        VALUES (:id, :data, :description_vector, :summary, :summary_vector)
        ON CONFLICT (id) DO NOTHING
    """)

    try:
        # Convert description_vector to JSON string format for each row
        batch_prepared = [
            {
                "id": row[0],
                "data": row[1],
                "description_vector": json.dumps(row[2]),  # Convert list to JSON string
                "summary": row[3],
                "summary_vector": json.dumps(row[4]),
            }
            for row in batch
        ]

        await session.execute(query, batch_prepared)
        await session.commit()
        logger.info(f"{len(batch)} rows inserted and committed in batch.")
    except Exception as e:
        logger.error(f"Batch insert failed: {e}")
        await session.rollback()


async def enable_age_extension(session):
    """
    Enable the Apache AGE extension and set the search path.
    """
    logger.info("Enabling the Apache AGE extension for Postgres...")
    await session.execute(text("CREATE EXTENSION IF NOT EXISTS age"))
    # await session.execute(text("LOAD 'age'"))
    await session.execute(text('SET search_path = ag_catalog, "$user", public;'))
    graph_name = "case_graph"
    await session.execute(text(f"SELECT create_graph('{graph_name}');"))


async def ingest_cases_to_graph_from_postgresql(session):
    """
    Ingest specific case text from PostgreSQL `cases_summary` table and create nodes in the graph.
    """
    query = text("""
        SELECT id, data -> 'casebody' -> 'opinions' -> 0 ->> 'text' AS text, summary AS summary
        FROM cases_summary;
    """)

    result = await session.execute(query)
    cases = result.fetchall()

    processed_rows = 0
    total_rows = len(cases)
    skipped_rows = 0
    error_count = 0  # Counter to keep track of the number of errors
    max_errors = 3  # Stop after 3 errors

    for case in cases:
        case_id, _, case_summary = case
        case_summary_sanitized = sanitize_case_text(case_summary)

        try:
            query = f"""
                SELECT * FROM cypher('case_graph', $$ 
                    CREATE (c:Case {{id: '{case_id}', summary: '{case_summary_sanitized}'}})
                $$) AS (c agtype);
            """
            await session.execute(text(query))

            processed_rows += 1

            # Commit every batch to ensure data is persisted
            if processed_rows % BATCH_SIZE == 0:
                await session.commit()

        except Exception as e:
            skipped_rows += 1
            error_count += 1
            logger.error(f"Skipped case {case_id} due to error: {e}")

            # Stop the process if 3 errors have occurred
            if error_count >= max_errors:
                logger.error(f"Encountered {error_count} errors. Stopping further processing.")
                break
            continue

    # Final commit after the loop
    await session.commit()

    logger.info(f"Inserted {processed_rows} case nodes into the graph from the PostgreSQL `cases` table.")
    logger.info(f"Skipped {skipped_rows} problematic cases.")


async def create_edges_from_citations(session):
    """
    Creates edges in the `case_graph` graph based on citation relationships
    in the `cases_summary` table.
    """
    define_edges_query = text("""
        WITH edges AS (
            SELECT DISTINCT c1.id AS id_from, c2.id AS id_to
            FROM cases_summary c1
            LEFT JOIN LATERAL jsonb_array_elements(c1.data -> 'cites_to') AS cites_to_element ON true
            LEFT JOIN LATERAL jsonb_array_elements(cites_to_element -> 'case_ids') AS case_ids ON true
            JOIN cases_summary c2 ON case_ids::text = c2.id
        )
        SELECT id_from, id_to FROM edges;
    """)

    result = await session.execute(define_edges_query)
    edges = result.fetchall()

    for id_from, id_to in edges:
        cypher_query = f"""
        SELECT * FROM ag_catalog.cypher('case_graph', $$
            MATCH (a:Case), (b:Case)
            WHERE a.id = '{id_from}' AND b.id = '{id_to}'
            CREATE (a)-[\:CITES]->(b)
            RETURN a, b
        $$) AS (a ag_catalog.agtype, b ag_catalog.agtype);
        """
        await session.execute(text(cypher_query))

    await session.commit()
    logger.info("Edges created successfully in the `case_graph` based on citation relationships.")


def sanitize_case_text(text):
    """
    Sanitize the case text to escape problematic characters.
    """
    if text is None:
        return ""

    # Escape single quotes by doubling them
    sanitized_text = text.replace("'", "")

    # Replace curly quotes with straight quotes
    sanitized_text = sanitized_text.replace("“", '"').replace("”", '"')

    # Replace en dash and em dash with simple dashes
    sanitized_text = sanitized_text.replace("–", "-").replace("—", "-")

    # Escape backslashes by doubling them
    sanitized_text = sanitized_text.replace("\\", "\\\\")

    sanitized_text = sanitized_text.replace("$", "")

    # Escape newlines and carriage returns
    sanitized_text = sanitized_text.replace("\n", "\\n").replace("\r", "\\r")

    return sanitized_text


async def main():
    parser = argparse.ArgumentParser(description="Create database schema")
    parser.add_argument("--host", type=str, help="Postgres host")
    parser.add_argument("--username", type=str, help="Postgres username")
    parser.add_argument("--password", type=str, help="Postgres password")
    parser.add_argument("--database", type=str, help="Postgres database")
    parser.add_argument("--sslmode", type=str, help="Postgres sslmode")

    # if no args are specified, use environment variables
    args = parser.parse_args()
    if args.host is None:
        engine = await create_postgres_engine_from_env()
    else:
        engine = await create_postgres_engine_from_args(args)

    await seed_data_from_csv(engine)

    await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.setLevel(logging.INFO)
    load_dotenv(override=True)
    asyncio.run(main())
