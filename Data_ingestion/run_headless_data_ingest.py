# %%
# %pip install sshtunnel
# %pip install requests
# %pip install psycopg
# %pip install pgvector
# %pip install python-dotenv


# %%
ALL_REPORTERS = ['a2d','a3d','abb-ct-app','abb-pr','abb-pr-ns','abbn-cas','ad','ad2d','ad3d','add','aik',
                 'ala','ala-app','alaska','alaska-fed','am-samoa','am-samoa-2d','am-samoa-3d','am-tribal-law',
                 'ant-np-cas','app-dc','ariz','ariz-app','ark','ark-app','ark-terr-rep','armstrong-election-cases',
                 'balt-c-rep','barb','barb-ch','binn','blackf','bland','blume-sup-ct-trans','blume-unrep-op','br',
                 'brad','bradf','brayt','brightly','bta','bur','cai','cai-cas','cal','cal-2d','cal-3d','cal-4th',
                 'cal-5th','cal-app','cal-app-2d','cal-app-3d','cal-app-4th','cal-app-5th','cal-dist-ct',
                 'cal-rptr-3d','cal-super-ct','cal-unrep','ccpa','chand','charlton','charlton-rep','cin-sup-ct-rep',
                 'cl-ch','cl-ct','cma','coffey','cole-cai-cas','cole-cas','colo','colo-app','colo-l-rep','colo-n-p',
                 'conn','conn-app','conn-cir-ct','conn-supp','connoly-sur-rep','cow','ct-cust','ct-intl-trade',
                 'cust-ct','d-chip','d-haw','dakota','dall','dallam','daly-ny','davis-l-ct-cas','day','dc',
                 'dc-patent','del','del-cas','del-ch','dem-sur','denio','disney-ohio','doug','dudley-rep',
                 'ed-pa','ed-smith','edm-sel-cas','edw-ch','f','f-appx','f-cas','f-supp','f-supp-2d',
                 'f-supp-3d','f2d','f3d','fed-cl','fla','fla-supp','fla-supp-2d','foster','frd',
                 'freem-ch','g-j','ga','ga-app','ga-l-rep','georgia-decisions','gibb-surr','gill','goebel',
                 'grant','greene','guam','gunby','h-g','h-j','h-mch','handy','harr-ch','haw','haw-app','hay-haz',
                 'hill','hill-den','hilt','hoff-ch','hopk-ch','hoseas-rep','how-app-cas','how-pr','how-pr-ns',
                 'howell-np','howison','idaho','ill','ill-2d','ill-app','ill-app-2d','ill-app-3d','ill-cir-ct-rep',
                 'ill-ct-cl','ind','ind-app','ind-l-rep','indian-terr','iowa','jeff','johns','johns-cas','johns-ch',
                 'kan','kan-app','kan-app-2d','keyes','kirby','ky','ky-op','l-ed-2d','la','la-ann','la-app','lans',
                 'lans-ch','law-times-ns','liquor-tax-rep','lock-rev-cas','mann-unrep-cas','mart-ns','mart-os',
                 'mass','mass-app-ct','mass-app-dec','mass-app-div','mass-app-div-annual','mass-l-rptr','mass-supp',
                 'mccahon','mcgl','mcgrath','md','md-app','md-ch','me','mich','mich-app','mich-np-r','mich-pr',
                 'miles','mills-surr','minn','minor','misc','misc2d','misc3d','miss','miss-dec','miss-s-m-ch','mj',
                 'mo','mo-app','monaghan','mont','mor-st-cas','morris','myrick','n-chip','n-mar-i','n-mar-i-commw',
                 'navajo-rptr','nc','nc-app','nd','ne2d','ne3d','neb','neb-app','nev','nh','nj','nj-eq',
                 'nj-manumission','nj-misc','nj-super','nj-tax','njl','nm','nm-app','nw2d','ny','ny-2d',
                 'ny-city-ct-rep','ny-crim','ny-proc-ct-ass','ny-st-rep','ny-sup-ct','ny-super-ct','ny3d',
                 'nys','ohio','ohio-app','ohio-app-2d','ohio-app-3d','ohio-app-unrep','ohio-ca','ohio-cc',
                 'ohio-cc-dec','ohio-cc-ns','ohio-ch','ohio-cir-dec','ohio-law-abs','ohio-lr','ohio-misc',
                 'ohio-misc-2d','ohio-np','ohio-np-ns','ohio-st','ohio-st-2d','ohio-st-3d','okla','okla-crim',
                 'or','or-app','or-tax','p2d','p3d','pa','pa-admiralty','pa-commw','pa-d-c','pa-d-c2d','pa-d-c3d',
                 'pa-d-c4th','pa-d-c5th','pa-fid','pa-just-l-rep','pa-super','paige-ch','park-crim-rep','parsons',
                 'pears','pelt','pen-w','pennyp','pin','port','posey','pow-surr','pr','pr-dec','pr-fed','pr-sent',
                 'rawle','rec-co-ch-sc','rec-co-ct','rec-va-ct-ri','redf','rep-cont-el','rep-cont-elect-case','ri',
                 'ri-dec','rob','robards','root','s-ct','sadler','sand-ch','sarat-ch-sent','sc','sc-eq','scdc-ns',
                 'scl','sd','se2d','seld-notes','serg-rawl','shan-cas','silv-ct-app','silv-sup','smith-n-h','so',
                 'so2d','so3d','stew','stew-p','super-ct-jud','super-ct-ri','sw','sw2d','sw3d','tapp-rep','tc','tca',
                 'teiss','tenn','tenn-app','tenn-ch-r','tenn-crim-app','tex','tex-civ-app','tex-crim','tex-ct-app',
                 'tex-l-r','thomp-cook','trans-app','tuck-surr','tyl','unrep-tenn-cas','us','us-app-dc','us-ct-cl',
                 'utah','utah-2d','va','va-app','va-ch-dec','va-cir','va-col-dec','va-dec','va-patt-heath','vaux',
                 'vet-app','vi','vt','w-va','walk-ch','walker','wash','wash-2d','wash-app','wash-terr','watts',
                 'watts-serg','wend','whart','wheel-cr-cas','white-w','willson','wilson','wis','wis-2d','wright',
                 'wv-ct-cl','wyo','yeates']
REPORTER = "wash-2d"


# %%
import os
from dotenv import load_dotenv

load_dotenv()

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
from psycopg import errors

def get_db_connection(mode="local"):
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
#pip install beautifulsoup4

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
#  """)
cur.execute("""
CREATE TABLE IF NOT EXISTS volumes(
	id text primary key unique,
	volume_number int,
	reporter_slug text,
	data jsonb
);
""")
# conn.commit()
# Fetch the data from the URL
for reporter in ALL_REPORTERS:
    url = f"https://static.case.law/{reporter}/VolumesMetadata.json"
    response = requests.get(url)
    data = response.json()
    print(url)
    print(json.dumps(data))
    
    # Insert the data into the reporters table

    for item in data:
        # Insert the data into the reporters table
        cur.execute("SELECT 1 FROM volumes WHERE id = %s", (str(item.get("id")),))
        if cur.fetchone():
            print(url)
            continue
        else:
            print(url)
            print(item)
            volume_number = int(''.join(filter(str.isdigit, item.get("volume_number"))))
            cur.execute("INSERT INTO volumes (id, volume_number, reporter_slug, data) VALUES (%s, %s, %s, %s)", (item.get("id"), volume_number, item.get("reporter_slug"), json.dumps(item)))
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
for reporter in ALL_REPORTERS:
    url = f"https://static.case.law/{reporter}/ReporterMetadata.json"
    response = requests.get(url)
    data = response.json()
    #print(json.dumps(data))
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

for reporter in ALL_REPORTERS:
    NUM_OF_VOLUMES = int(get_number_of_volumes_in_reporter(reporter))
    for i in range(NUM_OF_VOLUMES, 1, -1):
        # Fetch the data from the URL
        url = f"https://static.case.law/{reporter}/{i}/CasesMetadata.json"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            print(data)
            
            # Insert the data into the reporters table
            for item in data:
                cur.execute("SELECT 1 FROM cases_metadata WHERE id = %s", (str(item.get("id")),))
                if cur.fetchone():
                    print(f"Skipping {url}, already exists.")
                    continue
                
                try:
                    cur.execute("INSERT INTO cases_metadata (id, data) VALUES (%s, %s)", (item.get("id"), json.dumps(item)))
                    conn.commit()
                except errors.UniqueViolation:
                    print(f"Duplicate key value violates unique constraint: {item.get('id')}")
                    conn.rollback()
        else:
            print(f"Failed to fetch data from {url}, status code: {response.status_code}")

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

for reporter in ALL_REPORTERS:
# Fetch the data from the URL
    NUM_OF_VOLUMES = int(get_number_of_volumes_in_reporter(reporter))
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



