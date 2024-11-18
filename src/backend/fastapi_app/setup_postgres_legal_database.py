import argparse
import asyncio
import logging

from sqlalchemy import text

from fastapi_app.postgres_engine import create_postgres_engine_from_args, create_postgres_engine_from_env
from fastapi_app.postgres_models import Base

logger = logging.getLogger("legalcaseapp")


async def create_db_schema(engine, ml_endpoint, ml_key):
    async with engine.begin() as conn:
        logger.info("Enabling azure_ai extension...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS azure_ai"))

        logger.info("Enabling the pgvector extension for Postgres...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Set Azure ML endpoint and key
        logger.info("Setting Azure ML endpoint and API key...")
        await conn.execute(text(f"SELECT azure_ai.set_setting('azure_ml.scoring_endpoint', '{ml_endpoint}');"))
        await conn.execute(text(f"SELECT azure_ai.set_setting('azure_ml.endpoint_key', '{ml_key}');"))

        # Create the semantic_relevance function
        logger.info("Creating semantic_relevance function...")
        await conn.execute(
            text("""
            CREATE OR REPLACE FUNCTION semantic_relevance(query TEXT, n INT)
            RETURNS jsonb AS $$
            DECLARE
                json_pairs jsonb;
                result_json jsonb;
            BEGIN
                json_pairs := generate_json_pairs(query, n);
                result_json := azure_ml.invoke(
                    json_pairs,
                    deployment_name => 'bge-v2-m3-1',
                    timeout_ms => 180000
                );
                RETURN (
                    SELECT result_json as result
                );
            END $$ LANGUAGE plpgsql;
        """)
        )

        logger.info("Creating database tables and indexes...")
        await conn.run_sync(Base.metadata.create_all)

        # Enable the Apache AGE extension and load the library
        logger.info("Enabling the Apache AGE extension for Postgres...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS age;"))
        await conn.execute(text('SET search_path = ag_catalog, "$user", public;'))

    await conn.close()


async def main():
    parser = argparse.ArgumentParser(description="Create database schema")
    parser.add_argument("--host", type=str, help="Postgres host")
    parser.add_argument("--username", type=str, help="Postgres username")
    parser.add_argument("--password", type=str, help="Postgres password")
    parser.add_argument("--database", type=str, help="Postgres database")
    parser.add_argument("--sslmode", type=str, help="Postgres sslmode")
    parser.add_argument("--mlendpoint", type=str, help="AZURE ML SCORING ENDPOINT")
    parser.add_argument("--mlkey", type=str, help="AZURE ML ENDPOINT KEY")

    # if no args are specified, use environment variables
    args = parser.parse_args()
    if args.host is None:
        engine = await create_postgres_engine_from_env()
    else:
        engine = await create_postgres_engine_from_args(args)
        ml_endpoint = args.mlendpoint
        ml_key = args.mlkey

    await create_db_schema(engine, ml_endpoint, ml_key)

    await engine.dispose()

    logger.info("Database extension and tables created successfully.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    logger.setLevel(logging.INFO)
    asyncio.run(main())
