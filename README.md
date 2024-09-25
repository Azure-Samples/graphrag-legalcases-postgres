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

# Hackathon Descriptions

## Using Postgres and GraphRAG to improve accuracy of GenAI application

### 1. Problem
Today many customers complain about the accuracy for their GenAI application. Often the application hallucination and return incorrect answers, especially in enterprise scenarios when a lot of the answers are hidden in documents specific to the company or their industry.

### 2. Use case
Created a legal research application based on 7 million available cases in the US to help lawyers and legal professionals enhance their case preparation process.

By leveraging Postgres and GenAI, PAID aims to provide them with powerful tools to:​

- Identify Relevant Cases: Quickly find and analyze case law pertinent to their current cases.​

- Highlight Key Precedents: Connect cases through pivotal rulings and opinions to strengthen legal arguments.​

- Improve Productivity: Streamline workflows and make case preparation more efficient.​

Overall, it’s about empowering legal professionals with advanced technology to build stronger, more informed cases.​

### 3. Solution
Using Postgres and advanced techniques we can improve the quality of the context used by the LLM to improve answers.

We are going to use the following techniques and demonstrate how graphs can significantly improve content.:

- Vector search: Can be inaccurate due to the limitation with embeddings​.
- Semantic reranker: Improves on Vector results however has no reference about relationships and why 1 result might be more important that another.
- Graph: The most superior solution. Lawyers care the most about prominence of a case there are referencing to define the strongest cases. We create a graph and to see prominence and improved results, by ranking results with more citations higher. Using a graph, we were about to detect with cases are most relevant to a question and has the most references.​

### Azure Technologies used
#### Azure Database for PostgreSQL - Flexible Server:

- Stores large volumes of structured related to all cases were stored in Postgres.
- Used Postgres Azure AI extension to embed all the case data
- Used Postgres to perform vector search and reranker queries.
- Used Postgres graph extension to perform graph query

#### Azure OpenAI:

- Utilized for OpenAI embedding model to embed all the cases data.
- Using GPT4o to answer the user questions using the retrieved context.

#### Azure Machine Learning:

- Utilized to host the endpoint for the reranker model.

### 4. Dataset Used
The dataset used was all the cases in US history.

We ingested all cases from the [Case Law](https://case.law/), almost 7 million cases from courts all over the US.

- [Case Data](https://static.case.law/wash/198/cases/0001-01.json): Data about the case. Including Opinions from the judge, Case names, Judges etc.
- [Case Metadata](https://static.case.law/wash/198/CasesMetadata.json): Metadata about a case. Including case names, judges, court information, citation information etc.
- [Case Data embeddings]: We embedded all the opinions from a case and store. it as a column in the Case Data table.

### 5a. Business Value of Azure OpenAI to Microsoft Customers
**Improved Productivity:** Streamlines the research and preparation process, saving time and resources for professionals.

**Better Utilization of Data:** Enables the discovery of hidden, industry-specific insights within vast document repositories, turning data into actionable knowledge.

**Scalability and Flexibility:** Leverages Azure's scalable infrastructure, allowing for the efficient handling of large volumes of data with high performance and reliability. We were able to process millions of rows of data with Azure OpenAI.

### 5b. Business Value of Azure OpenAI to Microsoft Customers
**Enhanced Accuracy for RAG application:** With this hack we proved advanced techniques like Graph RAG can improve accuracy of RAG application, reducing the time and effort required for research tasks, allowing professionals to focus on higher-value tasks.​

**Operational Efficiency and Cost Saving:** With this hack we proved that enterprises could use Postgres for all the GenAI database needs, they don't need to migrate and learn new tech to develop high accurate and complex GenAI apps.

### 6. Demo
Imaging you a lawyer prepping for a case involving water leaking into the apartment:

**Q:** Water leaking into the apartment from the floor above. What are the prominent legal precedents in Washington on this problem?

**A:** Accurate generateed LLM answer using information from the Graph Query:

"The prominent legal precedents in Washington regarding water leaking into an apartment from the floor above are based on two main legal principles: the duty of care in maintaining premises and the implied warranty of habitability.

### 1. **Duty of Care in Maintaining Premises**
This principle holds landlords responsible for maintaining the premises in a safe and habitable condition, especially when defects are known or should have been known to them. The landlord must ensure that the property does not pose a danger to the tenants.

#### **Prominent Cases:**
- **Martindale Clothing Co. v. Spokane & Eastern Trust Co.** (1914): The court held the landlord liable for damages caused by water leaking from a pipe in the upper story, which the landlord failed to maintain properly. The landlord's negligence in maintaining the water pipe led to the flooding of the tenant's store, causing significant damage.
- **Thomas v. Housing Authority of the City of Bremerton** (1967): The court found the landlord liable for injuries caused by excessively hot water from a water heater, which was a known defect. The landlord's failure to maintain the water heater in a safe condition constituted negligence.
- **Jorgensen v. Massart** (1963): The court held that the landlord was responsible for damages caused by water leaking into the tenant's apartment due to the landlord's failure to maintain the building's roof properly.

### 2. **Implied Warranty of Habitability**
This principle implies that landlords must provide and maintain rental properties in a condition fit for human habitation. This includes ensuring that essential services such as plumbing are functional and do not pose health hazards.

#### **Prominent Cases:**
- **Foisy v. Wyman** (1973): The court recognized the implied warranty of habitability, holding that landlords must maintain rental properties in a habitable condition. The tenant was allowed to present evidence of the landlord's failure to repair significant defects, including water leaks, as a defense in an unlawful detainer action.
- **Stuart v. Coldwell Banker Commercial Group, Inc.** (1987): The court extended the implied warranty of habitability to condominium units, requiring that common areas and limited common areas be maintained in a condition fit for their intended use. The landlord was held liable for failing to address water leaks and other defects.

### Summary
In Washington, landlords are required to maintain rental properties in a safe and habitable condition. Failure to address known defects, such as water leaks from the floor above, can result in liability for damages under the principles of duty of care and implied warranty of habitability. Prominent cases such as Martindale Clothing Co. v. Spokane & Eastern Trust Co., Thomas v. Housing Authority of the City of Bremerton, Jorgensen v. Massart, Foisy v. Wyman, and Stuart v. Coldwell Banker Commercial Group, Inc. illustrate these principles and the legal obligations of landlords."
