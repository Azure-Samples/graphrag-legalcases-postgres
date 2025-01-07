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
csv.field_size_limit(2147483647)

logger = logging.getLogger("legalcaseapp")

BATCH_SIZE = 100


async def initialize_gold_dataset(session: AsyncSession):
    """
    Drop, create, and populate the gold_dataset table.
    """
    queries = [
        "DROP TABLE IF EXISTS gold_dataset;",
        """
        CREATE TABLE gold_dataset (
            gold_id TEXT,
            label TEXT
        );
        """,
        """
        INSERT INTO gold_dataset (gold_id, label)
        VALUES
            ('782330', 'orig-vector'), ('615468', 'gold-graph'), ('1095193', 'gold-graph'), ('1034620', 'gold-graph'), 
            ('772283', 'gold'), ('1186056', 'gold-graph'), ('1127907', 'gold-graph'), ('591482', 'gold'), 
            ('594079', 'gold-graph'), ('561149', 'gold'), ('1086651', 'orig'), ('2601920', 'gold-graph'), 
            ('552773', 'gold'), ('1346648', 'orig-semantic'), ('4912975', 'gold'), ('999494', 'gold'), 
            ('1005731', 'gold-semantic'), ('828223', 'gold'), ('4920250', 'gold'), ('4933418', 'gold'), 
            ('798646', 'gold'), ('768356', 'gold-semantic'), ('1017660', 'gold-vector'), ('4953587', 'maybe-graph'), 
            ('630224', 'maybe-semantic'), ('481657', 'maybe-semantic'), ('634444', 'no'), ('4975399', 'no'), 
            ('1279441', 'no'), ('1091260', 'no'), ('821843', 'no'), ('674990', 'no'), ('5041745', 'no'), 
            ('4938756', 'no'), ('473788', 'gold-graph-appeals'), ('3977147', 'no'), ('1352760', 'no'), 
            ('5752736', 'no');
        """,
    ]

    for query in queries:
        await session.execute(text(query))
    await session.commit()
    logger.info("gold_dataset table initialized successfully.")


async def seed_data_from_csv(engine: AsyncEngine, app_identity_name):
    csv_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "data/cases_final.csv"))
    logger.info(f"Starting data seeding from {csv_file_path} using parameterized INSERT statements.")

    async with AsyncSession(engine) as session:
        await initialize_gold_dataset(session)

        batch = []
        try:
            with open(csv_file_path, encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    case_id = row["id"]
                    data = json.loads(row["data"])

                    description_vector_str = row["description_vector"]
                    description_vector = json.loads(description_vector_str)

                    # Add row to the batch
                    batch.append((case_id, json.dumps(data), description_vector))

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

        await create_plpgsql_functions(session, app_identity_name)

        # # Insert cases as nodes in the graph
        await ingest_cases_to_graph_from_postgresql(session, app_identity_name)

        # # Create edges based on citations
        await create_edges_from_citations(session)

        await verify_age_query(session, app_identity_name)


async def insert_batch(session: AsyncSession, batch):
    """
    Insert a batch of rows into the database.
    """
    query = text("""
        INSERT INTO cases_updated (id, data, description_vector)
        VALUES (:id, :data, :description_vector)
        ON CONFLICT (id) DO NOTHING
    """)

    try:
        # Convert description_vector to JSON string format for each row
        batch_prepared = [
            {
                "id": row[0],
                "data": row[1],
                "description_vector": json.dumps(row[2]),  # Convert list to JSON string
            }
            for row in batch
        ]

        await session.execute(query, batch_prepared)
        await session.commit()
        logger.info(f"{len(batch)} rows inserted and committed in batch.")
    except Exception as e:
        logger.error(f"Batch insert failed: {e}")
        await session.rollback()


async def ingest_cases_to_graph_from_postgresql(session, app_identity_name):
    """
    Ingest specific case text from PostgreSQL `cases_updated` table and create nodes in the graph.
    """
    query = text("""
        SELECT id, data -> 'casebody' -> 'opinions' -> 0 ->> 'text' AS text
        FROM cases_updated;
    """)

    result = await session.execute(query)
    cases = result.fetchall()

    processed_rows = 0
    total_rows = len(cases)
    skipped_rows = 0
    error_count = 0  # Counter to keep track of the number of errors
    max_errors = 3  # Stop after 3 errors

    await session.execute(text("CREATE EXTENSION IF NOT EXISTS age;"))
    await session.execute(text('SET search_path = ag_catalog, "$user", public;'))
    graph_name = "case_graph"

    await session.execute(text(f"SELECT create_graph('{graph_name}');"))

    logger.info("case_graph database is created successfully.")

    # New grants on case_graph schema
    await session.execute(text(f'GRANT ALL ON SCHEMA case_graph TO "{app_identity_name}";'))
    await session.execute(text(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA case_graph TO "{app_identity_name}";'))
    await session.commit()
    logger.info("Granted permissions to the case_graph schema.")

    await session.execute(text('GRANT ALL ON SCHEMA case_graph TO "legalcaseadmin";'))
    await session.execute(text('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA case_graph TO "legalcaseadmin";'))
    await session.commit()
    await session.execute(text('GRANT USAGE ON SCHEMA public TO "legalcaseadmin"'))
    await session.execute(text('GRANT CREATE ON SCHEMA public TO "legalcaseadmin"'))
    await session.execute(text('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "legalcaseadmin"'))
    await session.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            'GRANT SELECT, UPDATE, INSERT, DELETE ON TABLES TO "legalcaseadmin"'
        )
    )
    await session.commit()
    logger.info("Granted privileges on schema case_graph to legalcaseadmin.")

    query = """
            SELECT create_case_in_case_graph(cases_updated.id) 
            FROM public.cases_updated;
        """
    await session.execute(text(query))

    await session.commit()

    logger.info(f"Inserted {processed_rows} case nodes into the graph from the PostgreSQL `cases` table.")
    logger.info(f"Skipped {skipped_rows} problematic cases.")


async def create_edges_from_citations(session):
    """
    Creates edges in the `case_graph` graph based on citation relationships
    in the `cases_updated` table.
    """
    try:
        query_prep = """
            WITH edges AS (
                SELECT c1.id AS id_from, c2.id AS id_to
                FROM public.cases_updated c1
                LEFT JOIN 
                    LATERAL jsonb_array_elements(c1.data -> 'cites_to') AS cites_to_element ON true
                LEFT JOIN 
                    LATERAL jsonb_array_elements(cites_to_element -> 'case_ids') AS case_ids ON true
                JOIN public.cases_updated c2 
                    ON case_ids::text = c2.id
                LIMIT 10
            )
            SELECT create_case_link_in_case_graph(edges.id_from, edges.id_to) 
            FROM edges
            limit 1;
        """
        await session.execute(text(query_prep))
        await session.commit()

        query_edges = """
            WITH edges AS (
                SELECT DISTINCT c1.id AS id_from, c2.id AS id_to
                FROM public.cases_updated c1
                LEFT JOIN 
                    LATERAL jsonb_array_elements(c1.data -> 'cites_to') AS cites_to_element ON true
                LEFT JOIN 
                    LATERAL jsonb_array_elements(cites_to_element -> 'case_ids') AS case_ids ON true
                JOIN public.cases_updated c2 
                    ON case_ids::text = c2.id
            ), gedges AS (
                SELECT edges.id_from, node1.id AS gid_from, edges.id_to, node2.id AS gid_to
                FROM edges
                LEFT JOIN case_graph."case" node1 ON node1.properties ->> 'case_id'::text = edges.id_from
                LEFT JOIN case_graph."case" node2 ON node2.properties ->> 'case_id'::text = edges.id_to
            )
            INSERT INTO case_graph."REF" (start_id, end_id)
            SELECT gid_from AS start_id, gid_to AS end_id
            FROM gedges where gid_from is not null and gid_to is not null;
        """
        await session.execute(text(query_edges))
        await session.commit()
        logger.info("Edges created successfully in the `case_graph` based on citation relationships.")
    except Exception as e:
        logger.error(f"Error creating edges in the `case_graph`: {e}")
        await session.rollback()


async def verify_age_query(session, app_identity_name):
    await session.execute(text("CREATE EXTENSION IF NOT EXISTS age;"))
    await session.execute(text('SET search_path = ag_catalog, "$user", public;'))

    cypher_query_count = """
    SELECT * from cypher('case_graph', $$
                    MATCH (n)
                    RETURN COUNT(n.case_id)
                $$) as (case_id TEXT);
    """

    await session.execute(text(cypher_query_count))

    await session.commit()
    await session.execute(text(f'GRANT ALL ON SCHEMA case_graph TO "{app_identity_name}";'))
    await session.execute(text(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA case_graph TO "{app_identity_name}";'))
    await session.commit()
    await session.execute(text('GRANT ALL ON SCHEMA case_graph TO "legalcaseadmin";'))
    await session.execute(text('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA case_graph TO "legalcaseadmin";'))
    await session.commit()
    logger.info("AGE queries are verified.")


async def create_plpgsql_functions(session, app_identity_name):
    function_graphrag = text("""
        CREATE OR REPLACE FUNCTION get_vector_semantic_graphrag_optimized(
            query_text TEXT,
            embedding VECTOR,
            top_n INT,
            consider_n INT,
            sort_option TEXT
        )
        RETURNS TABLE (
            label            TEXT,
            score            NUMERIC,
            graph_rank       BIGINT,
            semantic_rank    BIGINT,
            vector_rank      BIGINT,
            id               TEXT,
            case_name        TEXT,
            date             TEXT,
            data             JSONB,
            refs             BIGINT,
            relevance        DOUBLE PRECISION
        ) AS $_$
        BEGIN
            SET search_path = ag_catalog, "$user", public;

            RETURN QUERY
            WITH vector AS (
                SELECT cases_updated.id,
                    cases_updated.data#>>'{name_abbreviation}' AS case_name,
                    cases_updated.data#>>'{decision_date}' AS date,
                    cases_updated.data,
                    RANK() OVER (ORDER BY description_vector <=> embedding) AS vector_rank
                FROM cases_updated
                WHERE (cases_updated.data#>>'{court, id}')::integer IN (9029)
                ORDER BY description_vector <=> embedding
                LIMIT consider_n
            ),
            json_payload AS (
                SELECT jsonb_build_object(
                    'pairs', 
                    jsonb_agg(
                        jsonb_build_array(
                            query_text, 
                            LEFT(vector.data -> 'casebody' -> 'opinions' -> 0 ->> 'text', 800)
                        )
                    )
                ) AS json_pairs
                FROM vector
            ),
            semantic AS (
                SELECT elem.relevance::DOUBLE precision AS relevance, elem.ordinality
                FROM json_payload AS jp,
                    LATERAL jsonb_array_elements(
                        azure_ml.invoke(
                            jp.json_pairs,
                            deployment_name => 'bge-v2-m3-1',
                            timeout_ms => 180000
                        )
                    ) WITH ORDINALITY AS elem(relevance)
            ),
            semantic_ranked AS (
                SELECT RANK() OVER (ORDER BY semantic.relevance DESC) AS semantic_rank,
                    semantic.*, vector.*
                FROM vector
                JOIN semantic ON vector.vector_rank = semantic.ordinality
                ORDER BY semantic.relevance DESC
            ),      
            graph_query AS (
                SELECT * FROM ag_catalog.cypher('case_graph', 
                    $$ MATCH (s)-[r:REF]->(n) RETURN n.case_id AS case_id, s.case_id AS ref_id $$
                ) AS (case_id TEXT, ref_id TEXT)
            ),
            graph AS (
                SELECT subquery.id, COUNT(ref_id) AS refs
                FROM (
                    SELECT semantic_ranked.id, graph_query.ref_id, c2.description_vector <=> embedding AS ref_cosine
                    FROM semantic_ranked
                    LEFT JOIN graph_query
                    ON semantic_ranked.id = graph_query.case_id
                    LEFT JOIN cases_updated c2
                    ON c2.id = graph_query.ref_id
                    WHERE semantic_ranked.semantic_rank <= 25
                    ORDER BY ref_cosine
                    LIMIT 200
                ) AS subquery
                GROUP BY subquery.id
            ),
            graph2 AS (
                SELECT semantic_ranked.*, graph.refs 
                FROM semantic_ranked
                LEFT JOIN graph ON semantic_ranked.id = graph.id
            ),
            graph_ranked AS (
                SELECT RANK() OVER (ORDER BY COALESCE(graph2.refs, 0) DESC) AS graph_rank, graph2.*
                FROM graph2
                ORDER BY graph_rank DESC
            ),
            rrf AS (
                SELECT
                    gold_dataset.label,
                    COALESCE(1.0 / (60 + graph_ranked.graph_rank), 0.0) +
                    COALESCE(1.0 / (60 + graph_ranked.semantic_rank), 0.0) AS score,
                    graph_ranked.*
                FROM graph_ranked
                LEFT JOIN gold_dataset ON graph_ranked.id = gold_dataset.gold_id
            )
            SELECT 
                rrf.label, rrf.score, rrf.graph_rank, rrf.semantic_rank, rrf.vector_rank, rrf.id, rrf.case_name, rrf.date, rrf.data, rrf.refs, rrf.relevance
            FROM rrf
            ORDER BY 
                CASE 
                    WHEN sort_option = 'vector_rank' THEN rrf.vector_rank
                    WHEN sort_option = 'semantic_rank' THEN rrf.semantic_rank
                END ASC,
                CASE 
                    WHEN sort_option = 'score' THEN rrf.score
                END DESC
            LIMIT top_n;
        END;
        $_$ LANGUAGE plpgsql;
    """)
    await session.execute(function_graphrag)
    await session.commit()
    logger.info("Function get_vector_semantic_graphrag_optimized defined successfully.")

    function_age = text("""
        CREATE OR REPLACE FUNCTION initialize_age_extension()
        RETURNS void AS $_$
        BEGIN
        
            CREATE EXTENSION IF NOT EXISTS age;
            
            SET search_path = ag_catalog, "$user", public;

            BEGIN
                SELECT * FROM cypher('case_graph', $$
                    MATCH ()-[r:REF]->()
                    RETURN COUNT(r) AS cites_count
                $$) AS (cites_count agtype);
            EXCEPTION WHEN OTHERS THEN
                -- Log or handle the error as needed (optional)
                RAISE NOTICE 'First cypher statement failed: %', SQLERRM;
            END;
        
            -- Execute the second cypher statement with error handling
            BEGIN
                SELECT * FROM cypher('case_graph', $$
                    MATCH ()-[r:REF]->()
                    RETURN COUNT(r) AS cites_count
                $$) AS (cites_count agtype);
            EXCEPTION WHEN OTHERS THEN
                -- Log or handle the error as needed (optional)
                RAISE NOTICE 'Second cypher statement failed: %', SQLERRM;
            END;
                        
        END;
        $_$ LANGUAGE plpgsql;
    """)
    await session.execute(function_age)
    await session.commit()
    logger.info("Function initialize_age_extension defined successfully.")

    await session.execute(text("DROP FUNCTION IF EXISTS create_case_in_case_graph;"))
    await session.commit()
    create_case_in_case_graph = text("""
        CREATE OR REPLACE FUNCTION create_case_in_case_graph(case_id text)
        RETURNS void
        LANGUAGE plpgsql
        VOLATILE
        AS $BODY$
        BEGIN
            SET search_path = ag_catalog, "$user", public;
            EXECUTE format('SELECT * FROM cypher(''case_graph'', $$CREATE (\:case {case_id\: %s})$$) AS (a agtype);', quote_ident(case_id));
        END
        $BODY$;
    """)
    await session.execute(create_case_in_case_graph)
    await session.commit()
    logger.info("Function create_case_in_case_graph defined successfully.")

    await session.execute(text("DROP FUNCTION IF EXISTS create_case_link_in_case_graph;"))
    await session.commit()
    create_case_link_in_case_graph = text("""
        CREATE OR REPLACE FUNCTION create_case_link_in_case_graph(id_from text, id_to text)
        RETURNS void
        LANGUAGE plpgsql
        VOLATILE
        AS $BODY$
        BEGIN
            SET search_path = ag_catalog, "$user", public;
            EXECUTE format('SELECT * FROM cypher(''case_graph'', $$MATCH (a:case), (b:case) WHERE a.case_id = %s AND b.case_id = %s CREATE (a)-[e:REF]->(b) RETURN e$$) AS (a agtype);', quote_ident(id_from), quote_ident(id_to));
        END
        $BODY$;
    """)
    await session.execute(create_case_link_in_case_graph)
    await session.commit()
    logger.info("Function create_case_link_in_case_graph defined successfully.")


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
    parser.add_argument("--app-identity-name", type=str, help="Azure App Service identity name")

    # if no args are specified, use environment variables
    args = parser.parse_args()
    if args.host is None:
        engine = await create_postgres_engine_from_env()
    else:
        engine = await create_postgres_engine_from_args(args)

    await seed_data_from_csv(engine, args.app_identity_name)

    await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.setLevel(logging.INFO)
    load_dotenv(override=True)
    asyncio.run(main())
