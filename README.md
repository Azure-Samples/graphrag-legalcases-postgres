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

2. Run the frontend:

```bash
    cd src/frontend
    npm run dev
```

3. Open the browser at `http://localhost:5173/` and you will see the frontend.