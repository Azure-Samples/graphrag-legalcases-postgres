import os

from azure.identity import DefaultAzureCredential
from azure.mgmt.rdbms.postgresql import PostgreSQLManagementClient

# Set up the Azure authentication and client
credential = DefaultAzureCredential()
subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
resource_group_name = os.getenv("RESOURCE_GROUP_NAME")
server_name = os.getenv("POSTGRES_SERVER_NAME")

# Initialize the PostgreSQL management client
postgres_client = PostgreSQLManagementClient(credential, subscription_id)

# Retrieve the PostgreSQL server details
server = postgres_client.servers.get(resource_group_name, server_name)

# Print the PostgreSQL administrator username, including dynamic ID
postgres_username = server.administrator_login
print(f"PostgreSQL Username: {postgres_username}")
