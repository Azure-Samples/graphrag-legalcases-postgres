import csv
import json
import logging
import os
import sys

from dotenv import load_dotenv
from psycopg2 import connect

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("data_ingestion")

# Increase CSV field size limit
csv.field_size_limit(sys.maxsize)

# Define database connection parameters
conn_params = {
    "dbname": os.getenv("POSTGRES_DATABASE", "postgres"),
    "user": os.getenv("POSTGRES_USERNAME", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
}

# Batch size (number of rows to process in each batch)
BATCH_SIZE = 100


def setup_db_tables(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # Only create 'cases_metadata' and 'cases' tables
        table_creation_statements = [
            """
            CREATE TABLE IF NOT EXISTS cases_metadata (
                id TEXT PRIMARY KEY UNIQUE,
                data JSONB
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY UNIQUE,
                data JSONB,
                description_vector vector(1536)
            );
            """,
        ]

        for statement in table_creation_statements:
            cur.execute(statement)
        conn.commit()
        logger.info("Database tables created successfully.")


def ingest_cases_from_csv(conn, csv_file_path):
    with conn.cursor() as cur:
        total_rows = get_total_rows(csv_file_path)
        processed_rows = 0
        batch = []  # List to store rows for batch insertion

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
                    insert_batch(cur, conn, batch)
                    processed_rows += len(batch)
                    print_progress(processed_rows, total_rows)
                    batch = []  # Clear the batch after inserting

            # Insert any remaining rows in the last batch
            if batch:
                insert_batch(cur, conn, batch)
                processed_rows += len(batch)
                print_progress(processed_rows, total_rows)

        logger.info(f"Cases data ingested from {csv_file_path} successfully.")


def insert_batch(cur, conn, batch):
    """
    Insert a batch of rows into the database and commit the transaction
    """
    query = """
        INSERT INTO cases (id, data, description_vector)
        VALUES %s
        ON CONFLICT (id) DO NOTHING
    """
    args_str = ",".join(cur.mogrify("(%s, %s, %s)", row).decode("utf-8") for row in batch)
    cur.execute(query % args_str)
    conn.commit()  # Commit the batch
    logger.info(f"{len(batch)} rows inserted and committed in batch")


def print_progress(processed_rows, total_rows):
    """
    Print a progress bar based on the number of processed rows
    """
    progress = (processed_rows / total_rows) * 100
    bar_length = 50  # Length of the progress bar
    block = int(round(bar_length * progress / 100))
    bar = "#" * block + "-" * (bar_length - block)
    sys.stdout.write(f"\rProgress: [{bar}] {processed_rows}/{total_rows} ({progress:.2f}%)")
    sys.stdout.flush()


def get_total_rows(csv_file_path):
    """
    Get the total number of rows in the CSV file
    """
    with open(csv_file_path, encoding="utf-8") as file:
        reader = csv.DictReader(file)
        total_rows = sum(1 for row in reader)
    return total_rows


def main():
    csv_file_path = "/workspace/data/cases.csv"
    with connect(**conn_params) as conn:
        setup_db_tables(conn)
        logger.info("Table setup completed.")
        ingest_cases_from_csv(conn, csv_file_path)
        logger.info("Ingest cases completed.")


if __name__ == "__main__":
    main()
