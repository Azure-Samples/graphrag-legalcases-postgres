param name string
param location string = resourceGroup().location
param tags object = {}

// Output the existing PostgreSQL connection details
output POSTGRES_HOST string = ''  // Will be overridden by .env
output POSTGRES_USERNAME string = '' // Will be overridden by .env
output POSTGRES_DATABASE string = '' // Will be overridden by .env
