import argparse
import asyncio
import csv
import json
import logging
import os
import sys

import numpy as np
from dotenv import load_dotenv
from psycopg2.extensions import AsIs, register_adapter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from fastapi_app.dependencies import get_azure_credential
from fastapi_app.embeddings import compute_text_embedding
from fastapi_app.openai_clients import create_openai_embed_client
from fastapi_app.postgres_engine import create_postgres_engine_from_args, create_postgres_engine_from_env

csv.field_size_limit(sys.maxsize)
logger = logging.getLogger("legalcaseapp")
BATCH_SIZE = 100


async def insert_batch(session: AsyncSession, batch, table_name, query):
    """
    Insert a batch of rows into the specified table.
    """
    try:
        await session.execute(query, batch)
        await session.commit()
        logger.info(f"{len(batch)} rows inserted into {table_name} and committed in batch.")
    except Exception as e:
        logger.error(f"Batch insert failed for table {table_name}: {e}")
        await session.rollback()


async def create_table(session: AsyncSession, table_name, schema):
    """
    Create a table with the specified schema.
    """
    await session.execute(text(f"DROP TABLE IF EXISTS {table_name};"))
    await session.execute(text(schema))
    await session.commit()
    logger.info(f"Table `{table_name}` created successfully.")


async def initialize_table_from_csv(session: AsyncSession, csv_file_path, table_name, insert_query, process_row):
    """
    Generic function to initialize a table and populate it from a CSV file.
    """

    batch = []
    try:
        with open(csv_file_path, encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                processed_row = process_row(row)
                if processed_row:
                    batch.append(processed_row)

                # Insert batch into the database when the batch size is reached
                if len(batch) >= BATCH_SIZE:
                    await insert_batch(session, batch, table_name, insert_query)
                    batch = []  # Clear the batch after inserting

            # Insert any remaining rows in the last batch
            if batch:
                await insert_batch(session, batch, table_name, insert_query)

        logger.info(f"Data seeding completed successfully for table {table_name}.")
    except Exception as e:
        logger.error(f"Data seeding failed for table {table_name}: {e}")
        await session.rollback()


async def initialize_final_documents_table(engine: AsyncEngine):
    """
    Initialize and populate the `final_documents` table.
    """
    csv_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "data/final_documents.csv"))
    query = text("""
        INSERT INTO final_documents (id, human_readable_id, title, text, text_unit_ids, attributes)
        VALUES (:id, :human_readable_id, :title, :text, :text_unit_ids, :attributes)
        ON CONFLICT (id) DO NOTHING
    """)

    def process_row(row):
        try:
            attributes = json.loads(row["attributes"].replace("'", '"'))
            text_unit_ids = row["text_unit_ids"].strip("[]").split(",")
            return {
                "id": row["id"],
                "human_readable_id": row["human_readable_id"],
                "title": row["title"],
                "text": row["text"],
                "text_unit_ids": text_unit_ids,
                "attributes": json.dumps(attributes),
            }
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in row {row}: {e}")
            return None

    async with AsyncSession(engine) as session:
        await create_table(
            session,
            "final_documents",
            """
            CREATE TABLE final_documents (
                id TEXT PRIMARY KEY,
                human_readable_id TEXT,
                title TEXT,
                text TEXT,
                text_unit_ids TEXT[],
                attributes JSONB
            );
        """,
        )
        await initialize_table_from_csv(session, csv_file_path, "final_documents", query, process_row)


async def initialize_final_text_units_table(engine: AsyncEngine):
    """
    Initialize and populate the `final_text_units` table.
    """
    csv_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "data/final_text_units.csv"))
    query = text("""
        INSERT INTO final_text_units (id, human_readable_id, text, n_tokens, document_ids, entity_ids, relationship_ids)
        VALUES (:id, :human_readable_id, :text, :n_tokens, :document_ids, :entity_ids, :relationship_ids)
        ON CONFLICT (id) DO NOTHING
    """)

    def process_row(row):
        try:
            document_ids = row["document_ids"].strip("[]").split(",")
            entity_ids = row["entity_ids"].strip("[]").split(",")
            relationship_ids = row["relationship_ids"].strip("[]").split(",")
            return {
                "id": row["id"],
                "human_readable_id": row["human_readable_id"],
                "text": row["text"],
                "n_tokens": int(row["n_tokens"]),
                "document_ids": document_ids,
                "entity_ids": entity_ids,
                "relationship_ids": relationship_ids,
            }
        except Exception as e:
            logger.error(f"Error processing row {row}: {e}")
            return None

    async with AsyncSession(engine) as session:
        await create_table(
            session,
            "final_text_units",
            """
            CREATE TABLE final_text_units (
                id TEXT PRIMARY KEY,
                human_readable_id TEXT,
                text TEXT,
                n_tokens INT,
                document_ids TEXT[],
                entity_ids TEXT[],
                relationship_ids TEXT[]
            );
        """,
        )
        await initialize_table_from_csv(session, csv_file_path, "final_text_units", query, process_row)


async def initialize_final_communities_table(engine: AsyncEngine):
    """
    Initialize and populate the `final_communities` table.
    """
    csv_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "data/final_communities.csv"))
    table_name = "final_communities"
    schema = """
        CREATE TABLE final_communities (
            id TEXT PRIMARY KEY,
            human_readable_id TEXT,
            community INT,
            level INT,
            title TEXT,
            entity_ids TEXT[],
            relationship_ids TEXT[],
            text_unit_ids TEXT[],
            period TEXT,
            size INT
        );
    """
    query = text("""
        INSERT INTO final_communities (
            id, human_readable_id, community, level, title,
            entity_ids, relationship_ids, text_unit_ids, period, size
        )
        VALUES (
            :id, :human_readable_id, :community, :level, :title,
            :entity_ids, :relationship_ids, :text_unit_ids, :period, :size
        )
        ON CONFLICT (id) DO NOTHING
    """)

    def process_row(row):
        try:
            return {
                "id": row["id"],
                "human_readable_id": row["human_readable_id"],
                "community": int(row["community"]),
                "level": int(row["level"]),
                "title": row["title"],
                "entity_ids": row["entity_ids"].strip("[]").split(","),
                "relationship_ids": row["relationship_ids"].strip("[]").split(","),
                "text_unit_ids": row["text_unit_ids"].strip("[]").split(","),
                "period": row["period"],
                "size": int(row["size"]),
            }
        except Exception as e:
            logger.error(f"Error processing row {row}: {e}")
            return None

    async with AsyncSession(engine) as session:
        await create_table(session, table_name, schema)
        await initialize_table_from_csv(session, csv_file_path, table_name, query, process_row)


async def initialize_final_community_reports_table(engine: AsyncEngine):
    """
    Initialize and populate the `final_community_reports` table.
    """
    csv_file_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../..", "data/final_community_reports.csv")
    )
    table_name = "final_community_reports"
    schema = """
        CREATE TABLE final_community_reports (
            id TEXT PRIMARY KEY,
            human_readable_id TEXT,
            community INT,
            level INT,
            title TEXT,
            summary TEXT,
            full_content TEXT,
            rank TEXT,
            rank_explanation TEXT,
            findings TEXT,
            full_content_json TEXT,
            period TEXT,
            size TEXT,
            full_content_vector vector(1536)
        );
    """
    query = text("""
        INSERT INTO final_community_reports (
            id, human_readable_id, community, level, title, summary, full_content,
            rank, rank_explanation, findings, full_content_json, period, size
        )
        VALUES (
            :id, :human_readable_id, :community, :level, :title, :summary, :full_content,
            :rank, :rank_explanation, :findings, :full_content_json, :period, :size
        )
        ON CONFLICT (id) DO NOTHING
    """)

    def process_row(row):
        try:
            return {
                "id": row["id"],
                "human_readable_id": row["human_readable_id"],
                "community": int(row["community"]),
                "level": int(row["level"]),
                "title": row["title"],
                "summary": row["summary"],
                "full_content": row["full_content"],
                "rank": row["rank"],
                "rank_explanation": row["rank_explanation"],
                "findings": row["findings"],
                "full_content_json": row["full_content_json"],
                "period": row["period"],
                "size": row["size"],
            }
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error processing row {row['id'] if 'id' in row else 'unknown'}: {e}")
            return None

    async with AsyncSession(engine) as session:
        await create_table(session, table_name, schema)
        await initialize_table_from_csv(session, csv_file_path, table_name, query, process_row)


async def generate_and_update_embeddings(engine: AsyncEngine):
    """
    Generate embeddings for `full_content` and update the `full_content_vector` column.
    """
    update_query = text("""
        UPDATE final_community_reports
        SET full_content_vector = :vector
        WHERE id = :id
    """)

    select_query = text("""
        SELECT id, full_content
        FROM final_community_reports
        WHERE full_content_vector IS NULL
    """)

    def addapt_vector(nparray):
        """Adapt a numpy array to the PostgreSQL VECTOR type."""
        vector_str = ",".join(map(str, nparray.tolist()))
        return AsIs(f"'[{vector_str}]'::VECTOR")

    def adapt_vector(nparray):
        """Adapt a numpy array to the PostgreSQL VECTOR type."""
        return f"[{','.join(map(str, nparray.tolist()))}]"

    register_adapter(np.ndarray, addapt_vector)

    async with AsyncSession(engine) as session:
        async with session.begin():
            print("Generating embeddings and updating the database...")
            result = await session.execute(select_query)
            rows = result.fetchall()

            print(f"Found {len(rows)} rows to process.")

            for row in rows:
                try:
                    # Generate embeddings for `full_content`
                    azure_credential = await get_azure_credential()
                    openai_embed_client = await create_openai_embed_client(azure_credential)

                    embedding = await compute_text_embedding(
                        row[1],
                        openai_client=openai_embed_client,
                        embed_model="text-embedding-3-small",
                        embed_deployment="text-embedding-3-small",
                        embedding_dimensions=1536,
                    )

                    fcv = np.array(embedding)
                    if fcv is not None:
                        # Update the `full_content_vector` column
                        vector_str = adapt_vector(fcv)
                        await session.execute(
                            update_query,
                            {"vector": vector_str, "id": row[0]},
                        )
                except Exception as e:
                    logger.error(f"Error generating embeddings for row ID {row[0]}: {e}")
            await session.commit()


async def create_hnsw_index(engine: AsyncEngine):
    """
    Create the HNSW index on the `full_content_vector` column.
    """
    async with AsyncSession(engine) as session:
        async with session.begin():
            create_index_query = text("""
                CREATE INDEX IF NOT EXISTS idx_full_content_vector ON final_community_reports
                USING hnsw (full_content_vector vector_cosine_ops);
            """)
            await session.execute(create_index_query)
            await session.commit()
            logger.info("HNSW index on `full_content_vector` created successfully.")


async def main():
    parser = argparse.ArgumentParser(description="Seed PostgreSQL database with data from CSV files.")
    parser.add_argument("--host", type=str, help="Postgres host")
    parser.add_argument("--username", type=str, help="Postgres username")
    parser.add_argument("--password", type=str, help="Postgres password")
    parser.add_argument("--database", type=str, help="Postgres database")
    parser.add_argument("--sslmode", type=str, help="Postgres SSL mode")

    args = parser.parse_args()

    if args.host is None:
        engine = await create_postgres_engine_from_env()
    else:
        engine = await create_postgres_engine_from_args(args)

    await initialize_final_documents_table(engine)
    await initialize_final_text_units_table(engine)
    await initialize_final_communities_table(engine)
    await initialize_final_community_reports_table(engine)
    await generate_and_update_embeddings(engine)
    await create_hnsw_index(engine)
    await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.setLevel(logging.INFO)
    load_dotenv(override=True)
    asyncio.run(main())
