import logging
import os
import sys

import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("graph_db_ingestion")

# Define database connection parameters
conn_params = {
    "dbname": os.getenv("POSTGRES_DATABASE", "postgres"),
    "user": os.getenv("POSTGRES_USERNAME", "postgres"),
    "password": "Passwd34!",
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
}

# Batch size (number of rows to process in each batch)
BATCH_SIZE = 100


def setup_age_graph(conn):
    graph_name = "case_graph"
    with conn.cursor() as cur:
        # Ensure the AGE extension is enabled and loaded
        cur.execute("CREATE EXTENSION IF NOT EXISTS age;")
        cur.execute("LOAD 'age';")

        # Set the search_path to include the Apache AGE catalog
        cur.execute('SET search_path = ag_catalog, "$user", public;')

        conn.commit()

        cur.execute(f"SELECT create_graph('{graph_name}');")

        conn.commit()

        logger.info(f"Graph '{graph_name}' created successfully in Apache AGE.")


def ingest_cases_to_graph_from_postgresql(conn):
    """
    Ingest specific case text from PostgreSQL `cases` table and create nodes in the graph.
    Stop processing after encountering the first 3 errors.
    """
    with conn.cursor() as cur:
        # Query only the specific text from the 'opinions' field of the 'casebody'
        cur.execute("""
            SELECT id, data -> 'casebody' -> 'opinions' -> 0 ->> 'text' AS text, summary AS summary
            FROM cases_summary;
        """)
        cases = cur.fetchall()

        processed_rows = 0
        total_rows = len(cases)
        skipped_rows = 0
        error_count = 0  # Counter to keep track of the number of errors
        max_errors = 3  # Stop after 3 errors

        for case in cases:
            case_id, case_text, case_summary = case

            # Log the case ID and text to understand what's being processed
            logger.info(f"Processing case {case_id}")
            logger.debug(f"Case text: {case_text}")
            logger.debug(f"Case Summary: {case_summary}")

            case_summary_sanitized = sanitize_case_text(case_summary)
            # case_data_json = Json(case_text)
            try:
                # Use parameterized query to insert the case_id and case_text
                # cur.execute(
                #     """
                #     SELECT * FROM cypher('case_graph', $$
                #         CREATE (c:Case {id: %s, text: %s::jsonb})
                #     $$) AS (c agtype);
                # """,
                #     (case_id, case_data_json),
                # )
                cur.execute(
                    """
                    SELECT * FROM cypher('case_graph', $$ 
                        CREATE (c:Case {id: %s, summary: %s})
                    $$) AS (c agtype);
                    """,
                    (case_id, case_summary_sanitized),
                )

                processed_rows += 1
                print_progress(processed_rows, total_rows)

                # Commit every batch to ensure data is persisted
                if processed_rows % BATCH_SIZE == 0:
                    conn.commit()

            except psycopg2.Error as e:
                # Log the error, the case ID, and the text causing the issue
                skipped_rows += 1
                error_count += 1
                logger.error(f"Skipped case {case_id} due to error: {e}")
                logger.debug(f"Problematic text for case {case_id}: {case_text}")

                # Stop the process if 3 errors have occurred
                if error_count >= max_errors:
                    logger.error(f"Encountered {error_count} errors. Stopping further processing.")
                    break  # Exit the loop after 3 errors
                continue

        # Final commit after the loop
        conn.commit()

        logger.info(f"Inserted {processed_rows} case nodes into the graph from the PostgreSQL `cases` table.")
        logger.info(f"Skipped {skipped_rows} problematic cases.")


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


def create_edges_in_graph_from_postgresql(conn, batch_size=10):
    """
    Create edges (relationships) between nodes based on 'cites_to' field in PostgreSQL `cases` table.
    Only process cases where the 'cites_to' field is not an empty array.
    """
    with conn.cursor() as cur:
        offset = 0
        processed_edges = 0

        while True:
            # Query a batch of cases where 'cites_to' is not an empty array
            cur.execute(
                """
                SELECT id, data
                FROM cases
                WHERE data -> 'cites_to' != '[]'::jsonb
                LIMIT %s OFFSET %s;
            """,
                (batch_size, offset),
            )

            cases = cur.fetchall()
            if not cases:
                break  # No more cases to process

            for case in cases:
                case_id, case_data = case  # case_data is already a dictionary

                # Check if the case cites other cases (cites_to should be a list of dictionaries)
                cites_to = case_data.get("cites_to", [])
                if not isinstance(cites_to, list):
                    logger.error(f"Unexpected cites_to format in case {case_id}: {cites_to}")
                    continue

                # Gather all cited case IDs for the current case
                cited_case_ids = [
                    str(cited_id)  # Ensure IDs are treated as strings
                    for citation in cites_to
                    if isinstance(citation, dict)
                    for cited_id in citation.get("case_ids", [])
                ]

                if cited_case_ids:
                    # Convert the cited_case_ids list to a proper Cypher array format
                    cited_case_ids_str = "[" + ", ".join(f"'{cited_id}'" for cited_id in cited_case_ids) + "]"

                    # Construct the UNWIND query with MERGE to create edges between cases
                    cur.execute(
                        f"""
                        SELECT * FROM cypher('case_graph', $$ 
                            MATCH (c1:Case {{id: '{case_id}'}})
                            UNWIND {cited_case_ids_str} AS cited_case_id
                            MERGE (c2:Case {{id: cited_case_id}})
                            MERGE (c1)-[:CITES]->(c2)
                        $$) AS t(c agtype);
                        """
                    )

                    processed_edges += len(cited_case_ids)

            # Commit after processing each batch
            conn.commit()
            offset += batch_size

            # Print progress dynamically
            logger.info(f"Processed {processed_edges} edges so far...")

        # Final commit after the loop
        conn.commit()
        logger.info(
            "Finished inserting edges into the graph based on the 'cites_to' field in the PostgreSQL `cases` table."
        )

        # Validate the count of edges inserted
        cur.execute(
            """
            SELECT * FROM cypher('case_graph', $$ 
                MATCH (c1:Case)-[:CITES]->(c2:Case)
                RETURN COUNT(*) AS cites_count
            $$) AS t(cites_count BIGINT);
            """
        )
        cites_count = cur.fetchone()[0]
        logger.info(f"Validation check: {cites_count} edges found in the database.")


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


def main():
    # Connect to PostgreSQL
    with psycopg2.connect(**conn_params) as conn:
        # Step 1: Setup the AGE graph
        setup_age_graph(conn)

        # Step 2: Ingest cases as nodes into the graph from PostgreSQL
        ingest_cases_to_graph_from_postgresql(conn)

        # Step 3: Create edges based on 'cites_to' references from PostgreSQL
        # create_edges_in_graph_from_postgresql(conn)


if __name__ == "__main__":
    main()
