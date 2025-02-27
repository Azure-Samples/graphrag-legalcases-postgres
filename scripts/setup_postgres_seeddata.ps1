$POSTGRES_HOST = (azd env get-value POSTGRES_HOST)
if (-not $?) {
    Write-Host "Failed to find a value or POSTGRES_HOST in your azd environment. Make sure you run azd up first."
    exit 1
}
$POSTGRES_USERNAME = (azd env get-value POSTGRES_USERNAME)
$POSTGRES_DATABASE = (azd env get-value POSTGRES_DATABASE)
$APP_IDENTITY_NAME = (azd env get-value SERVICE_WEB_IDENTITY_NAME)

if ([string]::IsNullOrEmpty($POSTGRES_HOST) -or [string]::IsNullOrEmpty($POSTGRES_USERNAME) -or [string]::IsNullOrEmpty($POSTGRES_DATABASE)) {
    Write-Host "Can't find POSTGRES_HOST, POSTGRES_USERNAME, and POSTGRES_DATABASE environment variables. Make sure you run azd up first."
    exit 1
}

python ./src/backend/fastapi_app/setup_postgres_legal_seeddata.py --host $POSTGRES_HOST --username $POSTGRES_USERNAME --database $POSTGRES_DATABASE  --app-identity-name $APP_IDENTITY_NAME
