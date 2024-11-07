-- Vector query
WITH 
embedding_query AS (
    SELECT azure_openai.create_embeddings('text-embedding-3-small', query)::vector AS embedding
)
vector AS (
    SELECT cases.id
    FROM cases, embedding_query
    WHERE (cases.data#>>'{court, id}')::integer IN (9029, 8985) -- Washington Supreme Court (9029) or Washington Court of Appeals (8985)
    ORDER BY description_vector <=> embedding
    LIMIT 50
)
SELECT * FROM vector;

-- Semantic ranker query
WITH 
embedding_query AS (
    SELECT azure_openai.create_embeddings('text-embedding-3-small', query)::vector AS embedding
),
vector AS (
    SELECT cases.id
    FROM cases, embedding_query
    WHERE (cases.data#>>'{court, id}')::integer IN (9029, 8985) -- Washington Supreme Court (9029) or Washington Court of Appeals (8985)
    ORDER BY description_vector <=> embedding
    LIMIT 50
),
semantic AS (
    SELECT azure_ml.invoke(
				json_payload,
				deployment_name=>'bge-reranker-v2-m3')
    FROM generate_json_pairs(vector) AS json_payload
)
SELECT * FROM semantic;


-- Graph query
WITH 
embedding_query AS (
    SELECT azure_openai.create_embeddings('text-embedding-3-small', query)::vector AS embedding
),
vector AS (
    SELECT cases.id
    FROM cases, embedding_query
    WHERE (cases.data#>>'{court, id}')::integer IN (9029, 8985) -- Washington Supreme Court (9029) or Washington Court of Appeals (8985)
    ORDER BY description_vector <=> embedding
    LIMIT 50
),
semantic AS (
    SELECT *, azure_ml.invoke(
				 json_payload,
				 deployment_name=>'bge-reranker-v2-m3')) AS relevance,
           RANK() OVER (ORDER BY relevance DESC) AS semantic_rank
    FROM generate_json_pairs(vector) AS json_payload
),
graph AS (
    SELECT *, SELECT RANK() OVER (ORDER BY graph.refs DESC) AS graph_rank
    FROM semantic
	JOIN cypher('case_graph', $$
            MATCH ()-[r]->(n)
            RETURN n.case_id, COUNT(r) AS refs
        $$) as graph_query(case_id TEXT, refs BIGINT)
	ON semantic.id = graph_query.case_id
),
rrf AS (
    SELECT *,
        COALESCE(1.0 / (60 + graph_rank), 0.0) +
        COALESCE(1.0 / (60 + semantic_rank), 0.0) AS score
    FROM graph
    LIMIT 20
)
SELECT * FROM rrf;


WITH
embedding_query AS (
    SELECT azure_openai.create_embeddings('text-embedding-3-small', query)::vector AS embedding
),
vector AS (
    SELECT cases.id, RANK() OVER (ORDER BY description_vector <=> embedding) AS vector_rank
    FROM cases, embedding_query
    WHERE (cases.data#>>'{court, id}')::integer IN (9029, 8985) -- Washington Supreme Court (9029) or Washington Court of Appeals (8985)
    ORDER BY description_vector <=> embedding
    LIMIT 50
),
semantic AS (
    SELECT * 
    FROM semantic_relevance(query, 50)
),
semantic_ranked AS (
    SELECT semantic.relevance::DOUBLE PRECISION AS relevance, 
    FROM vector
    JOIN semantic ON vector.vector_rank = semantic.ordinality
    ORDER BY semantic.relevance DESC
),
graph AS (
    SELECT * from semantic_ranked
	JOIN cypher('case_graph', $$
            MATCH ()-[r]->(n)
            RETURN n.case_id, COUNT(r) AS refs
        $$) as graph_query(case_id TEXT, refs BIGINT)
	ON semantic_ranked.id = graph_query.case_id
),
graph_ranked AS (
    SELECT RANK() OVER (ORDER BY graph.refs DESC) AS graph_rank
    FROM graph ORDER BY graph_rank DESC
),
rrf AS (
    SELECT
        COALESCE(1.0 / (60 + graph_ranked.graph_rank), 0.0) +
        COALESCE(1.0 / (60 + semantic_ranked.semantic_rank), 0.0) AS score,
        semantic_ranked.*
    FROM graph_ranked
    JOIN semantic_ranked ON graph_ranked.id = semantic_ranked.id
    ORDER BY score DESC
    LIMIT 20
)
SELECT * 
FROM rrf;