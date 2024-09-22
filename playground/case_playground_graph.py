import psycopg2

# Database connection parameters
conn_params = {
    'dbname': 'mluk-genai-demo',
    'user': 'azureuser',
    'password': 'your_password',
    'host': 'your_host',
    'port': '5432'
}

# Connect to the PostgreSQL database
conn = psycopg2.connect(**conn_params)
cursor = conn.cursor()

# Create a graph if it doesn't exist
cursor.execute("SELECT create_graph('playground_case_graph');")

# Fetch data from the cases_playground table
cursor.execute("SELECT id, data->>'id' AS case_id, data->>'name' AS name FROM cases_playground;")
records = cursor.fetchall()

# Create vertices using Cypher
for record in records:
    id, case_id, name = record
    cypher_query = f"""
    SELECT * FROM cypher('playground_case_graph', $$
        CREATE (c:Case {{id: {id}, case_id: '{case_id}', name: '{name}'}})
    $$) AS (v agtype);
    """
    cursor.execute(cypher_query)

# Commit the transaction
conn.commit()

# Close the cursor and connection
cursor.close()
conn.close()

print("Vertices created successfully.")
