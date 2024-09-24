# PAID-mshacks
PAID (Postgres AI demos) Use PAID to get paid! In this day and age, the only way to increase revenue is to understand how to turn your Postgres application into an intelligent AI application. Learn quickly with this interactive Postgres App

## Running the frontend

1. Build the frontend:

```bash
    cd src/frontend
    npm install
    npm run build
    cd ../../
```

There must be an initial build of static assets before running the backend, since the backend serves static files from the `src/static` directory.

2. Run the FastAPI backend (with hot reloading). This should be run from the root of the project:

Clone the [Postgres and RAG demo](https://github.com/Azure-Samples/rag-postgres-openai-python/tree/main) as the backend. We hacked together the backend for this project. We need to build a proper backend. 

You need to install [Postgres on your local box](https://postgresapp.com/) to run this properly

```shell
    python -m uvicorn fastapi_app:create_app --factory --reload
```

Or you can run "Backend" in the VS Code Run & Debug menu.

3. Run the frontend (with hot reloading):

```bash
    cd src/frontend
    npm run dev
```

    Or you can run "Frontend" or "Frontend & Backend" in the VS Code Run & Debug menu.

4. Open the browser at `http://localhost:5173/` and you will see the frontend.
