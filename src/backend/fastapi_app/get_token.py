import asyncio
import logging
import os

from azure.identity import AzureDeveloperCliCredential, ManagedIdentityCredential

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_azure_credential():
    """
    Authenticate to Azure using Azure Developer CLI Credential or Managed Identity.
    Returns an instance of AzureDeveloperCliCredential or ManagedIdentityCredential.
    """
    try:
        if client_id := os.getenv("APP_IDENTITY_ID"):
            # Authenticate using a user-assigned managed identity on Azure
            # See web.bicep for the value of APP_IDENTITY_ID
            logger.info("Using managed identity for client ID %s", client_id)
            azure_credential = ManagedIdentityCredential(client_id=client_id)
        else:
            if tenant_id := os.getenv("AZURE_TENANT_ID"):
                logger.info(
                    "Authenticating to Azure using Azure Developer CLI Credential for tenant %s",
                    tenant_id,
                )
                azure_credential = AzureDeveloperCliCredential(tenant_id=tenant_id, process_timeout=60)
            else:
                logger.info("Authenticating to Azure using Azure Developer CLI Credential")
                azure_credential = AzureDeveloperCliCredential(process_timeout=60)
        return azure_credential
    except Exception as e:
        logger.warning("Failed to authenticate to Azure: %s", e)
        raise e


def get_password_from_azure_credential():
    """
    Fetch the Azure token using the credential obtained from get_azure_credential.
    Returns the token string.
    """

    async def get_token():
        azure_credential = await get_azure_credential()
        token = azure_credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
        return token.token

    # Run the asynchronous token retrieval in the event loop
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(get_token())


if __name__ == "__main__":
    try:
        password = get_password_from_azure_credential()
        print(password)
    except Exception as e:
        logger.error("Failed to retrieve password: %s", e)
