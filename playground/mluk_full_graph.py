import os
from decouple import Config, RepositoryEnv
from sshtunnel import SSHTunnelForwarder
import requests
import json
import os
import psycopg
import json
from tqdm import tqdm

def get_db_connection():
    # Setting up the SSH tunnel with tunnel credentials
    REMOTE_HOST = config("REMOTE_HOST")
    REMOTE_SSH_PORT = int(config("REMOTE_SSH_PORT"))
    PORT = int(config("PORT"))
    SSH_KEYFILE = config("SSH_KEYFILE")
    SSH_USERNAME =  config("SSH_USERNAME")

    server = SSHTunnelForwarder(
        ssh_address_or_host=(REMOTE_HOST, REMOTE_SSH_PORT),
        ssh_username= SSH_USERNAME,
        ssh_pkey=SSH_KEYFILE,
        remote_bind_address=('localhost', PORT)
    )
    server.start()
    print("server connected")

    conn_str = f"dbname=postgres host=localhost port={server.local_bind_port} user=postgres password={config('DB_PASSWORD')}"
    conn_str_formatted = f"postgresql://postgres:{config('DB_PASSWORD')}@localhost:{server.local_bind_port}/postgres"
    conn = psycopg.connect(conn_str)
    # conn.autocommit = True
    return conn_str_formatted, conn_str, conn

import pandas as pd
import json

def exec(query, params=()):
    try:
        with conn.cursor() as cur:
            cur.execute("""LOAD 'age';
                       SET search_path = ag_catalog, "$user", public;""")
            cur.execute(query, params)
            results = cur.fetchall()
            results_df = pd.DataFrame(results, columns=[desc[0] for desc in cur.description])
            return results_df
    except:
        conn.rollback()
        raise

def exec_enum(query, params=()):
    try:
        with conn.cursor() as cur1:
            cur1.execute("""LOAD 'age';
                        SET search_path = ag_catalog, "$user", public;""")
            cur1.close()
        with conn.transaction():
            with conn.cursor(name='my_cursor') as cur:
                cur.execute(query, params)
                while True:
                    results = cur.fetchmany(1000)  # Fetch in batches of 1000
                    if not results:
                        break
                    results_df = pd.DataFrame(results, columns=[desc[0] for desc in cur.description])
                    yield results_df
    except:
        conn.rollback()
        raise

config = Config(RepositoryEnv(".env"))
conn_str_formatted, conn_str, conn = get_db_connection()

try:
    exec("SELECT create_graph('case_graph_full');")
except:
    pass

# Delete all edges
exec("""SELECT * from cypher('case_graph', $$
        MATCH ()-[r]-()
        DELETE r
$$) as (V agtype);""")

# Delete all nodes
exec("""SELECT * from cypher('case_graph', $$
        MATCH (V)
        DELETE V
$$) as (V agtype);""")

df = exec(f"""
    SELECT c1.id AS id_from, c1.data ->> 'name_abbreviation' AS abbreviation, cites_to_element ->> 'cite' AS cite_to_id, c2.id AS id_to
    FROM cases c1
    LEFT JOIN 
        LATERAL jsonb_array_elements(c1.data -> 'cites_to') AS cites_to_element ON true
    LEFT JOIN 
        LATERAL jsonb_array_elements(cites_to_element -> 'case_ids') AS case_ids ON true
    JOIN cases c2 
        ON case_ids::text = c2.id
    LIMIT 1000;
    """)

distinct_id_from_count = df['id_from'].nunique()
total_rows = exec("SELECT COUNT(*) as c FROM cases;").iloc[0]['c']

all_data = []
for df in tqdm(exec_enum(f"""
    SELECT c1.id AS id_from, c1.data ->> 'name_abbreviation' AS abbreviation, cites_to_element ->> 'cite' AS cite_to_id, c2.id AS id_to
    FROM cases c1
    LEFT JOIN 
        LATERAL jsonb_array_elements(c1.data -> 'cites_to') AS cites_to_element ON true
    LEFT JOIN 
        LATERAL jsonb_array_elements(cites_to_element -> 'case_ids') AS case_ids ON true
    JOIN cases c2 
        ON case_ids::text = c2.id LIMIT 1000;
    """), total= round(total_rows / 81.0)):
    all_data.append(df)

final_df = pd.concat(all_data, ignore_index=True)
print(f"Total data: {final_df.shape}")

# Create nodes
print("Creating nodes...")
nodes = final_df['id_from'].unique()
print(nodes.shape)
for item in tqdm(nodes):
    exec(f"""SELECT * 
                FROM cypher('case_graph_full', $$
                    CREATE (:case {{case_id: '{item}'}})
                $$) as (v agtype);
          """)
    
# Create edges
print("Creating edges...")
for _, item in tqdm(final_df.iterrows(), total=final_df.shape[0]):
    exec(f"""
            SELECT * 
            FROM cypher('case_graph_full', $$
                MATCH (a:case), (b:case)
                WHERE a.case_id = '{item['id_from']}' AND b.case_id = '{item['id_to']}'
                CREATE (a)-[e:REF]->(b)
                RETURN e
            $$) as (e agtype);
        """)