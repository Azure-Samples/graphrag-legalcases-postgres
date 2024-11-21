POSTGRES_HOST=$(azd env get-value POSTGRES_HOST)
if [ $? -ne 0 ]; then
    echo "Failed to find a value or POSTGRES_HOST in your azd environment. Make sure you run azd up first."
    exit 1
fi
POSTGRES_USERNAME=$(azd env get-value POSTGRES_USERNAME)
POSTGRES_DATABASE=$(azd env get-value POSTGRES_DATABASE)
APP_IDENTITY_NAME=$(azd env get-value SERVICE_WEB_IDENTITY_NAME)

. ./scripts/load_python_env.sh

.venv/bin/python ./src/backend/fastapi_app/setup_postgres_legal_seeddata.py --host $POSTGRES_HOST --username $POSTGRES_USERNAME --database $POSTGRES_DATABASE  --app-identity-name $APP_IDENTITY_NAME
.venv/bin/python ./src/backend/fastapi_app/get_token.py > ./src/backend/fastapi_app/postgres_token.txt