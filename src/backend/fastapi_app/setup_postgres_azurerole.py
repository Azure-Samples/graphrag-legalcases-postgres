import argparse
import asyncio
import logging
import os
import sys

# Ensure proper path inclusion
current_dir = os.path.abspath(os.path.dirname(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(backend_dir)

# Path and debugging
print("Current sys.path:", sys.path)
print("Contents of backend_dir:", os.listdir(backend_dir))

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from fastapi_app.postgres_engine import create_postgres_engine_from_args, create_postgres_engine_from_env

logger = logging.getLogger("legalcaseapp")

async def create_ag_catalog_schema(engine):
    async with engine.begin() as conn:
        logger.info("Ensuring 'ag_catalog' schema exists...")
        create_schema_sql = """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'ag_catalog') THEN
                EXECUTE 'CREATE SCHEMA ag_catalog';
            END IF;
        END
        $$;
        """
        await conn.execute(text(create_schema_sql))

async def assign_role_for_webapp(engine, app_identity_name):
    async with engine.begin() as conn:
        await create_ag_catalog_schema(engine)
        logger.info(f"Creating PostgreSQL role for identity {app_identity_name}")
        await conn.execute(text(f"SELECT * FROM pgaadauth_create_principal('{app_identity_name}', false, false)"))
        logger.info(f"Granting permissions to {app_identity_name}")
        await conn.execute(text(f'GRANT USAGE ON SCHEMA ag_catalog TO "{app_identity_name}"'))

async def main():
    parser = argparse.ArgumentParser(description="Setup database for legal cases.")
    parser.add_argument("--host", required=True, help="Host for PostgreSQL")
    parser.add_argument("--username", required=True, help="Username for PostgreSQL")
    parser.add_argument("--database", required=True, help="Database name for PostgreSQL")
    parser.add_argument("--app_identity_name", required=True, help="App Identity Name for PostgreSQL role")
    args = parser.parse_args()

    print(f"Host: {args.host}")
    print(f"Username: {args.username}")
    print(f"Database: {args.database}")
    print(f"App Identity Name: {args.app_identity_name}")

    logger.info(f"Host: {args.host}")
    logger.info(f"Username: {args.username}")
    logger.info(f"Database: {args.database}")
    logger.info(f"App Identity Name: {args.app_identity_name}")

    engine = create_postgres_engine_from_args(args.host, args.username, args.database)
    await assign_role_for_webapp(engine, args.app_identity_name)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.setLevel(logging.INFO)
    load_dotenv(override=True)
    asyncio.run(main())