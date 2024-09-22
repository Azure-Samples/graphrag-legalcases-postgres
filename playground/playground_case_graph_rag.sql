LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- Create or replace the function
CREATE OR REPLACE FUNCTION get_vector_pagerank_graph_rrf_cases(query TEXT, top_n INT, consider_n INT)
RETURNS TABLE (
    score            NUMERIC,
    pagerank_rank    BIGINT,
    id               TEXT,
    vector_rank      BIGINT,
    abbr             TEXT,
    pagerank         NUMERIC,
    data             JSONB
) AS $$
DECLARE
    embedding VECTOR := azure_openai.create_embeddings('text-embedding-3-small', query)::vector;
BEGIN
    RETURN QUERY
    WITH vector AS (
        SELECT cases.id, RANK() OVER (ORDER BY description_vector <=> embedding) AS vector_rank, cases.data ->> 'name_abbreviation' AS abbr, (cases.data#>>'{analysis, pagerank, percentile}')::NUMERIC AS pagerank, cases.data
        FROM cases
        WHERE (cases.data#>>'{court, id}')::integer IN (9029) -- Washington Supreme Court (9029) or Washington Court of Appeals (8985)
        ORDER BY description_vector <=> embedding
        LIMIT consider_n
    ),
    graph_cases AS (
        SELECT id, data
        FROM cypher('pg2_case_graph', $$
            MATCH (c:Case)-[:CITES]->(cited:Case)
            WHERE c.data->>'description' ILIKE '%' || $1 || '%'
            RETURN cited.id AS id, cited.data AS data
        $$, query) AS (id TEXT, data JSONB)
    ),
    combined AS (
        SELECT RANK() OVER (ORDER BY vector.pagerank DESC) AS pagerank_rank, vector.*, graph_cases.id AS graph_id, graph_cases.data AS graph_data
        FROM vector
        LEFT JOIN graph_cases ON vector.id = graph_cases.id
        ORDER BY vector.pagerank DESC
    )
    SELECT
        COALESCE(1.0 / (60 + combined.vector_rank), 0.0) +
        COALESCE(1.0 / (60 + combined.pagerank_rank), 0.0) AS score,
        combined.*
    FROM combined
    ORDER BY score DESC
    LIMIT top_n;
END;
$$ LANGUAGE plpgsql;

-- Example query
SELECT * FROM get_vector_pagerank_graph_rrf_cases('Water leaking into the apartment from the floor above causing damages to the property.', 50, 50);
