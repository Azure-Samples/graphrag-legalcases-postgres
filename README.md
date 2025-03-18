# GraphRAG Solution Accelerator for Azure Database for PostgreSQL
This solution accelerator is designed as an end-to-end example of a Legal Research Copilot application. It demonstrates the implementation of three information retrieval techniques: vector search, semantic ranking, and GraphRAG on Azure Database for PostgreSQL, and illustrates how they can be combined to deliver high quality responses to legal research questions. The app uses the U.S. Case Law dataset of 0.5 million legal cases as a source of the factual data. For more details on these concepts, [please see the accompanying blog to this solution accelerator here](https://aka.ms/pg-graphrag).

## Solution Accelerator Architecture

<p align="center">
<img src="docs/assets/graph_rag_arch.png" style="width:70%; height:auto; display: block; margin: 0 auto;  text-align:center">
</p>

## Solution Accelerator Concepts

As the architecture diagram shows, this solution accelerator brings together **vector search, semantic ranking, and GraphRAG**. Here are some highlights, including the information retrieval pipeline:

<details>
  <summary><b>Semantic Ranking</b></summary>
    Enhances vector search accuracy by re-ranking results with a semantic ranker model, significantly improving top results' relevance (e.g., up to a 10–20% boost in NDCG@10 accuracy). The semantic ranker is available as a standalone solution accelerator, detailed in the blog: Introducing Semantic Ranker Solution Accelerator for Azure Database for PostgreSQL.
</details>

<details>
  <summary><b>GraphRAG</b></summary>
    An advanced RAG technique proposed by Microsoft Research to improve quality of RAG system responses by extracting knowledge graph from the source data and leveraging it to provide better context to the LLM. The GraphRAG technique consists of three high level steps:
    1. Graph extraction
    2. Entity summarization
    3. Graph query generation at query time
</details>

<details>
  <summary><b>Information Retrieval Pipeline</b></summary>
    We leverage the structure of the citation graph at the query time by using specialized graph query. The graph query is designed to use the prominence of the legal cases as a signal to improve the accuracy of the information retrieval pipeline. The graph query is expressed as a mixture of traditional relational query and OpenCypher graph query and executed on Postgres using the Apache AGE extension. The resulting information retrieval pipeline is shown below.
    <p align="center"><img src="docs/assets/info_pipeline.png" style="width:70%; height:auto; display: block; margin: 0 auto; text-align:center"></p>
</details>

## Further Reading
For related solution accelerators and articles please see the following:
- [Introducing GraphRAG Solution for Azure Database for PostgreSQL ](https://aka.ms/pg-graphrag)
- [Semantic Ranker Solution Accelerator for Azure Database for PostgreSQL](https://github.com/microsoft/Semantic-Ranker-Solution-PostgreSQL)
- [GraphRAG: Unlocking LLM discovery on narrative private data](https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-discovery-on-narrative-private-data/)
- [Reciprocal Rank Fusion (RRF) explained in 4 mins](https://medium.com/@devalshah1619/mathematical-intuition-behind-reciprocal-rank-fusion-rrf-explained-in-2-mins-002df0cc5e2a)

## Deployment and Development
The steps below guides you to deploy the Azure services necessary for this solution accelerator into your Azure subscription.

### Prerequisite Steps for Semantic Ranking ML Endpoint

⚠️ **NOTE:** In order to run the Semantic Ranking part of this accelerator, it requires you have an Azure ML Endpoint running a ranking model such as “bge-reranker-v2-m3”.  As a way to get this up and running, you can deploy following related solution accelerator which will setup an Azure ML Endpoint for ranking scoring:

- [Semantic Ranking in Azure Database for PostgreSQL Flexible Server](https://github.com/microsoft/Semantic-Ranker-Solution-PostgreSQL)

👉 Follow the steps in the repo above first before moving on to the deployment steps below.

👉 Once you deploy this accelerator, notate the `"/score"` REST endpoint URI and the key.  You will need these in the steps below when deploying.

### Deployment Steps For using Posix (sh)
1. Enter the following to clone the GitHub repo containing exercise resources:
    ```bash
    git clone https://github.com/Azure-Samples/graphrag-legalcases-postgres.git
    cd graphrag-legalcases-postgres
    ```
2. Use sample .env to create your own .env
    ```bash
    cp .env.sample .env
    ```
3. Edit your new .env file to add your Azure ML Semantic Ranker endpoints
    - Use the values obtained during the Prerequisite Steps above.
    - Replace the values between the {} with your values for each.
    ```bash
    AZURE_ML_SCORING_ENDPOINT={YOUR-AZURE-ML-ENDPOINT}
    AZURE_ML_ENDPOINT_KEY={YOUR-AZURE-ML-ENDPOINT-KEY}
    AZURE_ML_DEPLOYMENT={YOUR-AZURE-ML-ENDPOINT-KEY}
    ```
4. Login to your Azure account
    ```bash
    azd auth login
    ```
5. Provision the resources
    ```bash
    azd up
    ```
    - Enter a name that will be used for the resource group.
    - This will provision Azure resources and deploy this sample to those resources, including Azure Database for PostgreSQL Flexible Server, Azure OpenAI service, and Azure Container App Service.


### Deployment Steps For using Windows (pwsh)

We recommend and have targeted the use of the sh shell. You can run the provided devcontainer setup by pressing CTRL + Shift + P in Visual Studio Code and selecting the 'Dev Containers: Rebuild and Reopen in Container' option. This will give you access to an sh shell for your work even if you are using a Windows environment.

However, if you prefer to use your Windows environment directly with pwsh instead, you’ll need to follow these steps:

1. Install azd (https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd?tabs=winget-windows%2Cbrew-mac%2Cscript-linux&pivots=os-windows)

2. Install PowerShell (PowerShell-7.4.6-win-x64.msi-> https://github.com/PowerShell/PowerShell/releases/tag/v7.4.6)

3. Install Rust (rustup-init.exe ->https://rustup.rs/)

4. Install Python 3.12 (Windows installer (64-bit)-> https://www.python.org/downloads/release/python-3120/)

5. Install Node.js (https://nodejs.org/en).

After that, you need to open a new terminal and run these two commands manually. Please note that for Linux it is not required to run these manually, only for Windows, you need to run:
```
pip install -r requirements-dev.txt
pip install -e src/backend
```
After completing the above steps, you need to follow the steps provided in [Deployment Steps For using Posix (sh)](#deployment-steps-for-using-posix-sh) above.

## Troubleshooting

### Common Issues and Resolutions

1. **Errors During Deployment (`azd up`)**
   If you encounter any errors during the deployment process, run `azd down` to clean up the resources and address the issue. Once resolved, you can run `azd up` again to retry the deployment.

2. **Missing URLs or Configuration**
   If you lose track of the deployment URLs or configuration, you can use the `azd show` command to display the existing URLs and other deployment details.

3. **Checking Region Capacity**
   Before running `azd up`, ensure that your target region has the desired available capacity for your deployment. You can refer to the `main.parameters.json` file to check the capacity needed for Chat, Eval, and Embedding generations. By default, ensure the following minimum capacities or you can try to modify these parameters in the `main.parameters.json` file accordingly if you do not have enough available capacity in your Azure subscription.
     - **GPT-4o:** 30K - AZURE_OPENAI_CHAT_DEPLOYMENT_CAPACITY
     - **GPT-4:** 80K - AZURE_OPENAI_EVAL_DEPLOYMENT_CAPACITY
     - **text-embedding-3-small:** 120K - AZURE_OPENAI_EMBED_DEPLOYMENT_CAPACITY

4. **Azure Subscription Permissions**
   Ensure that you have the appropriate permissions in your Azure subscription. You should be the **subscription owner** or have equivalent permissions to successfully deploy resources and enable required features.

### MSR GraphRAG Integration (optional)


You can run the default integration with MSR GraphRAG data by selecting the corresponding option from the frontend. However, if you want to run entire Microsoft's GraphRAG integration alongside our RRF graph solution, follow the steps below to initialize, auto-tune, and index the `graphrag` folder for your data. The output of these GraphRAG steps is already available in the data folder. However, if you prefer to run the library yourself, follow the steps below. If you’d rather use the provided CSV files directly, you can skip ahead to step 8.


### 1. Create the Necessary Folder Structure
Run the following command to create the required folder structure:
```
mkdir -p ./graphrag/input
```

Before running the GraphRAG library, you need to prepare and place the input CSV file into the `./graphrag/input` folder. You will need to create the input CSV file in the following steps.

### 2. Extracting Relevant Data from the Original Table
The original case table contains multiple columns, including:

- `id` – Unique identifier for each case.
- `data` – A large JSON object containing detailed case information.
- `description_vector` – A 1536-dimensional vector used for vector search.

However, not all json fields from `data` are required for GraphRAG processing. To simplify the dataset, we will create a filtered table (`cases_filtered`) that retains only the necessary columns while excluding the `description_vector` and create a csv file from it in the next step.

```sql
CREATE TABLE cases_filtered (
    id TEXT,
    name TEXT,
    court_id TEXT,
    court_name TEXT,
    description TEXT
);


INSERT INTO cases_filtered (id, name, court_id, court_name, description)
SELECT
    id,
    data->>'name' AS name,
    (data->'court'->>'id') AS court_id,
    data->'court'->>'name' AS court_name,
    data->'casebody'->'opinions'->0->>'text' AS description
FROM cases_updated;
```

Please note that original case table is already provided in data folder as `cases_final.csv` after `azd up` command, you will obtain it in a table format named `cases_updated`.

### 3. Exporting Data to CSV
To generate the required CSV file, run the following SQL command inside your PostgreSQL database:

```sql
COPY (
    SELECT id, name, court_id, court_name, description
    FROM demo_cases_filtered
) TO '/home/postgres/cases_filtered_final.csv'
WITH CSV HEADER;
```

This command extracts the required fields from `demo_cases_filtered` and saves them as `cases_filtered_final.csv` inside the PostgreSQL container.

### 4. Copying the CSV File to the Input Directory
Next, copy the generated CSV file from the PostgreSQL container to your local input directory:

```bash
docker cp <container-name>:/home/postgres/cases_filtered_final.csv /<your-path>/graphrag/input/cases_filtered_final.csv
```

Replace `<container-name>` with the actual name of your running PostgreSQL container and `<your-path>` with the local directory path where the GraphRAG input folder is located.

Ensure that the file `cases_filtered_final.csv` is correctly placed inside `./graphrag/input/` before running the GraphRAG library.

### 5. Install Dependencies
Activate the Poetry environment by running:
```
poetry shell
poetry install
```
This will install the necessary dependencies to use the `graphrag` command.


### 6. Initialize the Folder
Initialize the folder with the following command:
```
graphrag init --root ./graphrag
```
This will create the required files for the process.


### 7. Configure API Keys and Settings
- Provide your `GRAPHRAG_API_KEY` in the `.env` file, depending on the OpenAI model type you are using.
- Update the `settings.yaml` file with the following configuration with your data columns instead:


```
input:
  type: file  # or 'blob'
  file_type: csv  # or 'text'
  base_dir: "input"
  file_encoding: utf-8
  file_pattern: ".*\\.csv$"
  source_column: id
  text_column: description
  title_column: name
  document_attribute_columns:
    - court_id
    - court_name
```

- Update the `settings.yaml` file with the following model configuration for your Azure OpenAI.

```
llm:
  api_key: ${GRAPHRAG_API_KEY}
  type: azure_openai_chat
  model: gpt-4o-mini
  model_supports_json: true
  api_base: https://<your-azure-openai>.openai.azure.com
  api_version: <your-azure-openai-4o-mini-version>
  deployment_name: gpt-4o-mini
```

```
embeddings:
  async_mode: threaded # or asyncio
  vector_store:
    type: lancedb
    db_uri: 'output/lancedb'
    container_name: default
    overwrite: true
  llm:
    api_key: ${GRAPHRAG_API_KEY}
    type: azure_openai_embedding
    model: text-embedding-3-small
    api_base: https://<your-azure-openai>.openai.azure.com
    api_version: <your-azure-openai-text-embedding-3-small-version>
    deployment_name: text-embedding-3-small
```

### 8. Run Auto-Tuning for Prompts
Auto-tune your prompts according to your data by running:
```
python -m graphrag prompt-tune --root ./graphrag/ --config ./graphrag/settings.yaml --no-discover-entity-types --output ./graphrag/prompts/
```

### 9. Run the Indexing Process
Begin the indexing process for your knowledge graph with:
```
graphrag index --root ./graphrag
```
This process may take about an hour to complete, depending on your rate limits.


### 10. Convert Parquet Files to CSV
After indexing, use the `notebook.ipynb` file to convert the following Parquet files to CSV and save them in the `data` folder:
- `final_documents`
- `final_text_units`
- `final_communities`
- `final_community_reports`
Once the CSV files are in the `data` folder, proceed to the next step to create additional vector fields and generate embeddings.

### 11. Generate embeddings
Embeddings need to be generated during post-provisioning to modify the CSV files for `final_text_units` and `final_community_reports`.

Before running the initial deployment, set the RUN_POST_EMBEDDING parameter to `true` in the `scripts/setup_postgres_seeddata.sh` file. This ensures that new fields are created and embeddings are generated. Then, execute:
```
azd up
```
Once the tables with embeddings are generated, convert them into CSV files and place them in the `data` folder. This will speed up future deployments.


### 12. Deploy Your Project
Finally, after generating the embeddings and saving them in CSV format, update the RUN_POST_EMBEDDING parameter to `false` in the `scripts/setup_postgres_seeddata.sh` file to prevent redundant processing.

Run the following command to complete the deployment:
```
azd up
```
If the server is already running, please execute the following command first to re-provision the servers:
```
azd down
```

## Notes
- Ensure all necessary configurations in `.env` and `settings.yaml` are accurate.
- Indexing time may vary based on your system and rate limits.
- If you encounter any issues, refer to the documentation or reach out for support.


## Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need
to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the
instructions provided by the bot. You will only need to do this once across all repositories using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft’s Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos are subject to those third-party’s policies.
