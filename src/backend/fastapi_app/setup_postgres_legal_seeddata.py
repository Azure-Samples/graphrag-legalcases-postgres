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
