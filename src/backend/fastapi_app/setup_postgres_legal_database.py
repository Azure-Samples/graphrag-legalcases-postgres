import argparse
import asyncio
import logging
import os
import sys

# Calculate the correct path to src/backend and add it to sys.path
current_dir = os.path.abspath(os.path.dirname(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(backend_dir)

# Verify paths
fastapi_app_dir = os.path.join(backend_dir, "fastapi_app")

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

        scoring_endpoint = os.getenv("AZURE_ML_SCORING_ENDPOINT")
        endpoint_key = os.getenv("AZURE_ML_ENDPOINT_KEY")

    if not scoring_endpoint or not endpoint_key:
        raise EnvironmentError("Azure ML endpoint settings missing.")

async def assign_role_for_webapp(engine, app_identity_name):
    async with engine.begin() as conn:
        # Ensure schema ag_catalog exists
        await conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'ag_catalog') THEN
                    CREATE SCHEMA ag_catalog;
                END IF;
            END
            $$;
        """))

        logger.info(f"Creating a PostgreSQL role for identity {app_identity_name}")
        await conn.execute(text(f"SELECT * FROM pgaadauth_create_principal('{app_identity_name}', false, false)"))

        logger.info(f"Granting permissions to {app_identity_name}")
        await conn.execute(text(f'GRANT USAGE ON SCHEMA ag_catalog TO "{app_identity_name}"'))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup database for legal cases.")
    parser.add_argument("--host", required=True, help="Host for PostgreSQL")
    parser.add_argument("--username", required=True, help="Username for PostgreSQL")
    parser.add_argument("--database", required=True, help="Database name for PostgreSQL")
    parser.add_argument("--app_identity_name", required=True, help="App Identity Name for PostgreSQL role")
    args = parser.parse_args()

    async def main():
        engine = create_postgres_engine_from_args(args.host, args.username, args.database)
        await assign_role_for_webapp(engine, args.app_identity_name)

    asyncio.run(main())