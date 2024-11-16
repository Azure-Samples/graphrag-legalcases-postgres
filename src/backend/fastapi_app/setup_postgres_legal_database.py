import argparse
import asyncio
import logging
import os

from dotenv import load_dotenv
from sqlalchemy import text

from fastapi_app.postgres_engine import create_postgres_engine_from_args, create_postgres_engine_from_env
from fastapi_app.postgres_models import Base

logger = logging.getLogger("legalcaseapp")


async def create_db_schema(engine):
    async with engine.begin() as conn:
        logger.info("Enabling azure_ai extension...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS azure_ai"))

        logger.info("Enabling the pgvector extension for Postgres...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Load environment variables for Azure ML endpoint settings
        scoring_endpoint = os.getenv("AZURE_ML_SCORING_ENDPOINT")
        endpoint_key = os.getenv("AZURE_ML_ENDPOINT_KEY")

        print("scoring_endpoint == ", scoring_endpoint)

        if not scoring_endpoint or not endpoint_key:
            logger.error(
                "Azure ML endpoint settings are missing. Please set AZURE_ML_SCORING_ENDPOINT and AZURE_ML_ENDPOINT_KEY in the environment."
            )
            return

        # Set Azure ML endpoint and key
        logger.info("Setting Azure ML endpoint and API key...")
        await conn.execute(text(f"SELECT azure_ai.set_setting('azure_ml.scoring_endpoint', '{scoring_endpoint}');"))
        await conn.execute(text(f"SELECT azure_ai.set_setting('azure_ml.endpoint_key', '{endpoint_key}');"))

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

    # if no args are specified, use environment variables
    args = parser.parse_args()
    if args.host is None:
        engine = await create_postgres_engine_from_env()
        # database_name = os.getenv("DATABASE_NAME")
        # host = os.getenv("DATABASE_HOST")
        # sslmode = os.getenv("DATABASE_SSLMODE", "require")
    else:
        engine = await create_postgres_engine_from_args(args)
        # database_name = args.database
        # host = args.host
        # sslmode = args.sslmode

    await create_db_schema(engine)

    await engine.dispose()

    logger.info("Database extension and tables created successfully.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    logger.setLevel(logging.INFO)
    load_dotenv(override=True)
    asyncio.run(main())
