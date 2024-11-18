# GraphRAG Solution Accelerator for Azure Database for PostgreSQL
This solution accelerator is designed as an end-to-end example of a Legal Research Copilot application. It demonstrates the implementation of three information retrieval techniques: vector search, semantic ranking, and GraphRAG on Azure Database for PostgreSQL, and illustrates how they can be combined to deliver high quality responses to legal research questions. The app uses the U.S. Case Law dataset of 0.5 million legal cases as a source of the factual data.

## Solution Accelerator Architecture

<img src="docs/assets/graph_rag_arch.png" style="width:70%; height:auto; display: block; margin: 0 auto;  text-align:center">

## Solution Accelerator Concepts

As the architecture diagram shows, this solution accelerator brings together vector search, semantic ranking, and GraphRAG.  This accompanying blog article covers these concepts in more detail, but here are some highlights, including the information retrieval pipeline:

> **Semantic Ranking:**
> Enhances vector search accuracy by re-ranking results with a semantic ranker model, significantly improving top results' relevance (e.g., up to a 10–20% boost in NDCG@10 accuracy). The semantic ranker is available as a standalone solution accelerator, detailed in the blog: Introducing Semantic Ranker Solution Accelerator for Azure Database for PostgreSQL.

> **GraphRAG:**
> An advanced RAG technique proposed by Microsoft Research to improve quality of RAG system responses by extracting knowledge graph from the source data and leveraging it to provide better context to the LLM. The GraphRAG technique consists of three high level steps:
> 1. Graph extraction 
> 2. Entity summarization 
> 3. Graph query generation at query time 

> **Information Retrieval Pipeline:**
> We leverage the structure of the citation graph at the query time by using specialized graph query. The graph query is designed to use the prominence of the legal cases as a signal to improve the accuracy of the information retrieval pipeline. The graph query is expressed as a mixture of traditional relational query and OpenCypher graph query and executed on Postgres using the Apache AGE extension. The resulting information retrieval pipeline is shown below.
> <img src="docs/assets/info_pipeline.png" style="width:70%; height:auto; display: block; margin: 0 auto; text-align:center">

## Further Reading
For related solution accelerators and articles please see the following:
- Full Blog on GraphRAG Solution for Azure Database for PostgreSQL
- Semantic Ranker Solution Accelerator for Azure Database for PostgreSQL
- GraphRAG: Unlocking LLM discovery on narrative private data

## Deployment and Development

### Deploy resources into your Azure subscription
The steps below guides you to deploy the Azure services necessary for this solution accelerator into your Azure subscription.
1. Enter the following to clone the GitHub repo containing exercise resources:
    ```bash
    git clone https://github.com/Azure-Samples/graphrag-legalcases-postgres.git
    cd graphrag-legalcases-postgres
    ```
2. Login to your Azure account
    ```bash
    azd auth login
    ```
3. Create a new azd environment
   ```bash
    azd env new
    ```
   Enter a name that will be used for the resource group. This will create a new folder in the .azure folder, and set it as the active environment for any calls to azd going forward.
4. Provision the resources
    ```bash
    azd up
    ```
    This will provision Azure resources and deploy this sample to those resources, including Azure Database for PostgreSQL Flexible Server, Azure OpenAI service, and Azure App Service.

### Development Locally in Development Container
The steps below guides you on how to develop locally using the provided development container:
TODO

## Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need
to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the
instructions provided by the bot. You will only need to do this once across all repositories using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft’s Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos are subject to those third-party’s policies.