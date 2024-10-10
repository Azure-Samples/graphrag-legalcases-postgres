LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- search
WITH
embedding_query AS (
    SELECT azure_openai.create_embeddings('text-embedding-3-small', 'Water leaking into the apartment from the floor above.')::vector AS embedding
),
vector AS (
    SELECT cases.id, RANK() OVER (ORDER BY description_vector <=> embedding) AS vector_rank
    FROM cases, embedding_query
    WHERE (cases.data#>>'{court, id}')::integer IN (9029)--, 8985) -- Washington Supreme Court (9029) or Washington Court of Appeals (8985)
    ORDER BY description_vector <=> embedding
    LIMIT 10
),
semantic AS (
    SELECT * 
    FROM jsonb_array_elements(
            semantic_relevance('Water leaking into the apartment from the floor above.',
            10)
        ) WITH ORDINALITY AS elem(relevance)
),
semantic_ranked AS (
    SELECT semantic.relevance::DOUBLE PRECISION AS relevance, semantic.*, vector.*
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
)
SELECT * FROM graph;


graph_ranked AS (
    SELECT RANK() OVER (ORDER BY graph.refs DESC) AS graph_rank, semantic_ranked.* 
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
		
-- query edges in cases table
SELECT c1.id AS id_from, c1.data ->> 'name_abbreviation', cites_to_element ->> 'cite' AS cite_to_id, c2.id AS id_to
FROM cases c1
LEFT JOIN 
    LATERAL jsonb_array_elements(c1.data -> 'cites_to') AS cites_to_element ON true
LEFT JOIN 
    LATERAL jsonb_array_elements(cites_to_element -> 'case_ids') AS case_ids ON true
JOIN cases c2 
	ON case_ids::text = c2.id
WHERE c1.id = '1857770';

SELECT data ->> 'name_abbreviation', data
		FROM cases
		WHERE data -> 'citations' -> 0 ->> 'cite'::text LIKE '%230%600%';
		   --OR id = '5265417';
		
SELECT data ->> 'name_abbreviation', data
FROM cases
WHERE data ->> 'name_abbreviation'::text LIKE '%Dubreuil%';


-- creation
SELECT create_graph('case_playground_graph');

SELECT * 
	FROM cypher('graph_name', $$
		MATCH (a:case), (b:case)
		WHERE a.case_id = '670242' AND b.case_id = '591482'
		CREATE d = (a)-[e:RELTYPE]->(b)
		RETURN d
	$$) as (d agtype);

commit;

SELECT * from cypher('graph_name', $$
                    MATCH (r:case)
                    RETURN r
                $$) as (r agtype);

SELECT * from cypher('graph_name', $$
                    MATCH ()-[r]->(n)
                    WHERE n.case_id IN ['782330', '615468']
                    RETURN r
                $$) as (r agtype);
				
WITH cases_data AS (
  SELECT id FROM cases_playground
)
SELECT * FROM cypher('case_playground_graph', $$
    UNWIND $cases_data AS row
    CREATE (e:Case {id: row.id})
    RETURN e.id
$$) AS result(id int);

-- doens't work
DO $fff$ 
DECLARE
    case_record RECORD;
BEGIN
    -- Step 1: Loop through the SQL results
    FOR case_record IN
        SELECT id FROM cases_playground
    LOOP
        -- Step 2: Execute Cypher query for each record
        PERFORM ag_catalog.cypher('case_playground_graph', $$
            CREATE (c:Case {id: $1})
            RETURN c
        $$, case_record.id::int);
    END LOOP;
END $fff$;
