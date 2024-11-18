POSTGRES_HOST=$(azd env get-value POSTGRES_HOST)
if [ $? -ne 0 ]; then
    echo "Failed to find a value or POSTGRES_HOST in your azd environment. Make sure you run azd up first."
    exit 1
fi
POSTGRES_USERNAME=$(azd env get-value POSTGRES_USERNAME)
POSTGRES_DATABASE=$(azd env get-value POSTGRES_DATABASE)
AZURE_ML_SCORING_ENDPOINT=$(azd env get-value AZURE_ML_SCORING_ENDPOINT)
AZURE_ML_ENDPOINT_KEY=$(azd env get-value AZURE_ML_ENDPOINT_KEY)

. ./scripts/load_python_env.sh

.venv/bin/python ./src/backend/fastapi_app/setup_postgres_legal_database.py --host $POSTGRES_HOST --username $POSTGRES_USERNAME --database $POSTGRES_DATABASE --mlendpoint $AZURE_ML_SCORING_ENDPOINT --mlkey $AZURE_ML_ENDPOINT_KEY
