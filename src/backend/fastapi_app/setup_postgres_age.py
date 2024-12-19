import logging
import os

import psycopg2

logger = logging.getLogger("legalcaseapp")


def configure_age(conn, app_identity_name):
    with conn.cursor() as cur:
        logger.info("AGE configuration...")

        # Execute the first query
        logger.info("Initializing AGE extension...")
        cur.execute("""SELECT * FROM initialize_age_extension();""")
        conn.commit()  # Commit after the first query

        # Execute the second query
        logger.info("Creating AGE extension if not exists...")
        cur.execute("""CREATE EXTENSION IF NOT EXISTS age;""")
        conn.commit()  # Commit after the second query

        # Execute the third query
        logger.info("Setting search_path...")
        cur.execute("""SET search_path = ag_catalog, "$user", public;""")
        conn.commit()  # Commit after the third query

        # Execute a MATCH query
        logger.info("Executing first MATCH query...")
        cur.execute(
            """SELECT * FROM cypher('case_graph', $$ 
                                    MATCH ()-[r:CITES]->() 
                                    RETURN COUNT(r) AS cites_count 
                                    $$) AS (cites_count agtype);"""
        )
        conn.commit()  # Commit after the MATCH query

        # Execute another MATCH query
        logger.info("Executing second MATCH query...")
        cur.execute(
            """SELECT * FROM cypher('case_graph', $$ 
                                    MATCH ()-[r:CITES]->() 
                                    RETURN COUNT(r) AS cites_count 
                                    $$) AS (cites_count agtype);"""
        )
        conn.commit()  # Commit after the second MATCH query

    logger.info("AGE configuration completed.")


def main():
    # Fetch environment variables
    host = os.getenv("POSTGRES_HOST")
    username = os.getenv("POSTGRES_ADMIN")
    database = os.getenv("POSTGRES_DATABASE")
    sslmode = os.getenv("POSTGRES_SSLMODE", "require")  # Default to 'require' SSL mode
    app_identity_name = os.getenv("APP_IDENTITY_NAME")

    filepath = os.path.join(os.path.dirname(__file__), "postgres_token.txt")
    with open(filepath) as file:
        password = file.read().strip()

    # Ensure environment variables are set
    if not all([host, username, password, database, app_identity_name]):
        raise ValueError("Missing required environment variables for database connection.")

    # Set SSL mode parameters
    sslmode_params = {}
    if sslmode.lower() in ["require", "verify-ca", "verify-full"]:
        sslmode_params["sslmode"] = sslmode

    try:
        # Connect to PostgreSQL using psycopg2
        conn = psycopg2.connect(
            host=host,
            user=username,
            password=password,
            dbname=database,
            **sslmode_params,
        )
        logger.info("Connected to the PostgreSQL database.")

        # Configure AGE
        configure_age(conn, app_identity_name)

    except Exception as e:
        logger.error(f"Failed to connect or configure the database: {e}")
        raise
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")

    logger.info("AGE configured successfully.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    logger.setLevel(logging.INFO)
    main()
