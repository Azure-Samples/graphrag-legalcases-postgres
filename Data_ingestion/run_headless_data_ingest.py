# %%
%pip install sshtunnel
%pip install requests
%pip install psycopg
%pip install pgvector
%pip install python-dotenv

# %%
%load_ext dotenv
%dotenv

# %% [markdown]
# ## Create Helper for the DB connection

# %%
from sshtunnel import SSHTunnelForwarder
import requests
import json
import os
import pgvector
import psycopg
from pgvector.psycopg import register_vector
import json

def get_db_connection(mode="remote"):
    if mode == "local":
        conn_str = f"dbname=postgres host=localhost port=5432 user=postgres password={os.getenv('DB_PASSWORD')}"
        return psycopg.connect(conn_str)
    
    if mode == "remote":
        REMOTE_HOST = os.getenv("REMOTE_HOST")
        REMOTE_SSH_PORT = int(os.getenv("REMOTE_SSH_PORT"))
        PORT = int(os.getenv("PORT"))
        SSH_KEYFILE = os.getenv("SSH_KEYFILE")
        SSH_USERNAME =  os.getenv("SSH_USERNAME")

        server = SSHTunnelForwarder(
            ssh_address_or_host=(REMOTE_HOST, REMOTE_SSH_PORT),
            ssh_username=SSH_USERNAME,
            ssh_pkey=SSH_KEYFILE,
            remote_bind_address=('localhost', PORT)
        )
        server.start()
        print(f"{mode} server connected")

        conn_str = f"dbname=postgres host=localhost port={server.local_bind_port} user=postgres password={os.getenv('DB_PASSWORD')}"
    
    else:
        conn_str = f"dbname=postgres host=localhost port=5432 user=postgres password={os.getenv('DB_PASSWORD')}"
    return psycopg.connect(conn_str)

# %% [markdown]
# ## Define Helper Methods to scrape website to get data

# %%
%pip install beautifulsoup4

# %% [markdown]
# ## Get all the cases in a volume

# %%
import requests
from bs4 import BeautifulSoup

def get_links_in_volume(reporter,volume):
    # URL of the page to parse
    url = f'https://static.case.law/{reporter}/{volume}/cases/'

    # Send a GET request to the URL
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all <a> tags with href attributes
        links = soup.find_all('a', href=True)
        links_array = []
        # Extract and print the file names
        for link in links:
            file_name = link['href'].split('/')[-1]
            #print(file_name)
            if not file_name == '':
                links_array.append(file_name)
    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    return links_array

# %% [markdown]
# ## Select Reporter

# %%
REPORTER = "wash-app"

# %%
get_links_in_volume(REPORTER, 1)

# %% [markdown]
# ## Get the number of vomules in a reporter

# %%
def get_number_of_volumes_in_reporter(reporter_name):
        # URL of the page to parse
    url = f'https://static.case.law/{reporter_name}/'
    # Send a GET request to the URL
    response = requests.get(url)
    volume_array = []

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all <a> tags with href attributes
        links = soup.find_all('a', href=True)
        # Extract and print the file names
        for link in links:
            file_name = link['href'].split('/')[-1]
            #print(file_name)
            if not file_name.endswith('json'):
                volume_array.append(file_name)
    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    return volume_array[-1].split(".")[0]

# %%
get_number_of_volumes_in_reporter(REPORTER)
NUM_OF_VOLUMES = int(get_number_of_volumes_in_reporter(REPORTER))


# %% [markdown]
# ## Create Volumes Table

# %%

# Setting up the SSH tunnel with tunnel credentials
# Connect to the database
conn = get_db_connection()
conn.autocommit = True
register_vector(conn)
cur = conn.cursor()
# Fetch descriptions from the listings table
# Create the reporters table
# cur.execute("""
# DROP TABLE volumes
# """)
# cur.execute("""
# CREATE TABLE IF NOT EXISTS volumes(
# 	id text primary key unique,
# 	volume_number int,
# 	reporter_slug text,
# 	data jsonb
# );
# """)
# conn.commit()
# Fetch the data from the URL

url = f"https://static.case.law/{REPORTER}/VolumesMetadata.json"
response = requests.get(url)
data = response.json()
print(json.dumps(data))
#print(data.get("id"))
# Insert the data into the reporters table
for item in data:
	cur.execute("INSERT INTO volumes (id, volume_number, reporter_slug, data) VALUES (%s, %s, %s, %s)", (item.get("id"), item.get("volume_number"), item.get("reporter_slug"), json.dumps(item)))
conn.commit()
# Close the cursor and connection
cur.close()

# %% [markdown]
# ## Create reporter Table

# %%

# Setting up the SSH tunnel with tunnel credentials
# Connect to the database
conn = get_db_connection()
conn.autocommit = True
register_vector(conn)
cur = conn.cursor()
# Fetch descriptions from the listings table
# Create the reporters table
# cur.execute("""
# DROP TABLE reporters
# """)
# cur.execute("""
# CREATE TABLE IF NOT EXISTS reporters(
# 	id text primary key,
# 	data jsonb
# );
# """)
# conn.commit()
# Fetch the data from the URL
url = f"https://static.case.law/{REPORTER}/ReporterMetadata.json"
response = requests.get(url)
data = response.json()
print(json.dumps(data))
#print(data.get("id"))
# Insert the data into the reporters table
cur.execute("SELECT 1 FROM reporters WHERE id = %s", (str(data.get("id")),))
if cur.fetchone():
	print(url)
else:
    cur.execute("INSERT INTO reporters (id, data) VALUES (%s, %s)", (data.get("id"), json.dumps(data)))
conn.commit()
# Close the cursor and connection
cur.close()

# %%

# Setting up the SSH tunnel with tunnel credentials
# Connect to the database
conn = get_db_connection()
conn.autocommit = True
register_vector(conn)
cur = conn.cursor()
# Fetch descriptions from the listings table
# Create the reporters table
# cur.execute("""
# DROP TABLE cases_metadata
# """)
# cur.execute("""
# CREATE TABLE IF NOT EXISTS cases_metadata(
# 	id text primary key unique,
# 	data jsonb
# );
# """)
# conn.commit()

for i in range(NUM_OF_VOLUMES+1, 1, -1):
	# Fetch the data from the URL
	url = f"https://static.case.law/{REPORTER}/{i}/CasesMetadata.json"
	response = requests.get(url)
	data = response.json()
	
	#print(data.get("id"))
	# Insert the data into the reporters table
	
	for item in data:
		cur.execute("SELECT 1 FROM cases_metadata WHERE id = %s", (str(item.get("id")),))
		if cur.fetchone():
			print(url)
			continue
		try:
			cur.execute("INSERT INTO cases_metadata (id, data) VALUES (%s, %s)", (item.get("id"), json.dumps(item)))
			print(json.dumps(data))
			conn.commit()
		except errors.UniqueViolation:
            #print(f"Duplicate key value violates unique constraint: {data.get('id')}")
			conn.rollback()
			
# Close the cursor and connection
cur.close()

# %% [markdown]
# ## Create the Cases Table will all the case data in a reporter

# %%
from psycopg import errors
# Setting up the SSH tunnel with tunnel credentials
# Connect to the database
conn = get_db_connection()
conn.autocommit = True
register_vector(conn)
cur = conn.cursor()
# Fetch descriptions from the listings table
# Create the reporters table
# cur.execute("""
# DROP TABLE cases
# """)
cur.execute("""
CREATE TABLE IF NOT EXISTS cases(
	id text primary key unique,
	data jsonb
);
""")
conn.commit()

# Fetch the data from the URL
for i in range(NUM_OF_VOLUMES, 0, -1):
    for case in get_links_in_volume(REPORTER,i):
        url = f"https://static.case.law/{REPORTER}/{i}/cases/{case}"
        
        response = requests.get(url)
        data = response.json()
        
        #print(data.get("id"))
        # Insert the data into the reporters table
        #cur.execute("INSERT INTO cases (id, data) VALUES (%s, %s)", (data.get("id"), json.dumps(data)))
        try:
            # Insert the data into the cases table
            print(url)
            cur.execute("INSERT INTO cases (id, data) VALUES (%s, %s)", (data.get("id"), json.dumps(data)))
            
            print(json.dumps(data))
            conn.commit()
        except errors.UniqueViolation:
            #print(f"Duplicate key value violates unique constraint: {data.get('id')}")
            conn.rollback()
        conn.commit()
        # Close the cursor and connection
cur.close()



