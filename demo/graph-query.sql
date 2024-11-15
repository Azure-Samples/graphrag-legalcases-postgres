LOAD 'age';
SET search_path = public, ag_catalog, "$user";

WITH
graph AS (
    SELECT *, RANK() OVER (ORDER BY graph_query.refs DESC) AS graph_rank
    FROM semantic_ranked semantic
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
SELECT score, graph_rank, semantic_rank, id, case_name, date, refs FROM rrf
ORDER BY score desc;