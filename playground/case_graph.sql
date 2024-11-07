LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- search
WITH
embedding_query AS (
    SELECT azure_openai.create_embeddings('text-embedding-3-small', 'Water leaking into the apartment from the floor above.')::vector AS embedding
),
vector AS (
    SELECT cases.id, cases.data#>>'{name_abbreviation}', RANK() OVER (ORDER BY description_vector <=> embedding) AS vector_rank
    FROM cases, embedding_query
    WHERE (cases.data#>>'{court, id}')::integer IN (9029)--, 8985) -- Washington Supreme Court (9029) or Washington Court of Appeals (8985)
    ORDER BY description_vector <=> embedding
    LIMIT 60
),
semantic AS (
    SELECT * 
    FROM jsonb_array_elements(
            semantic_relevance('Water leaking into the apartment from the floor above.',
            60)
        ) WITH ORDINALITY AS elem(relevance)
),
semantic_ranked AS (
    SELECT semantic.relevance::DOUBLE PRECISION AS relevance, RANK() OVER (ORDER BY relevance DESC) AS semantic_rank,
			semantic.*, vector.*
    FROM vector
    JOIN semantic ON vector.vector_rank = semantic.ordinality
    ORDER BY semantic.relevance DESC
),
graph AS (
    SELECT * from semantic_ranked
	LEFT JOIN cypher('case_graph_full', $$
            MATCH ()-[r]->(n)
            RETURN n.case_id, COUNT(r) AS refs
        $$) as graph_query(case_id TEXT, refs BIGINT)
	ON semantic_ranked.id = graph_query.case_id
),
graph_ranked AS (
    SELECT RANK() OVER (ORDER BY graph.refs DESC) AS graph_rank, graph.*
    FROM graph ORDER BY graph_rank DESC
),
rrf AS (
    SELECT
        COALESCE(1.0 / (60 + graph_ranked.graph_rank), 0.0) +
        COALESCE(1.0 / (60 + graph_ranked.semantic_rank), 0.0) AS score,
        graph_ranked.*
    FROM graph_ranked
    ORDER BY score DESC
    LIMIT 20
)
SELECT * 
FROM rrf;


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

CREATE OR REPLACE FUNCTION create_case(case_id text)
RETURNS void
LANGUAGE plpgsql
VOLATILE
AS $BODY$
BEGIN
	load 'age';
	SET search_path TO ag_catalog;
	EXECUTE format('SELECT * FROM cypher(''case_graph_full'', $$CREATE (:case {case_id: %s})$$) AS (a agtype);', quote_ident(case_id));
END
$BODY$;

CREATE OR REPLACE FUNCTION create_case_link(id_from text, id_to text)
RETURNS void
LANGUAGE plpgsql
VOLATILE
AS $BODY$
BEGIN
	load 'age';
	SET search_path TO ag_catalog;
	EXECUTE format('SELECT * FROM cypher(''case_graph_full'', $$MATCH (a:case), (b:case) WHERE a.case_id = %s AND b.case_id = %s CREATE (a)-[e:REF]->(b) RETURN e$$) AS (a agtype);', quote_ident(id_from), quote_ident(id_to));
END
$BODY$;

-- Delete all edges
DELETE FROM case_graph_full._ag_label_edge;
-- Delete all nodes
DELETE FROM case_graph_full._ag_label_vertex;

-- Create nodes
SELECT create_case(cases.id) 
FROM public.cases;

-- Create edges
WITH edges AS (
	SELECT c1.id AS id_from, c2.id AS id_to
	FROM public.cases c1
	LEFT JOIN 
	    LATERAL jsonb_array_elements(c1.data -> 'cites_to') AS cites_to_element ON true
	LEFT JOIN 
	    LATERAL jsonb_array_elements(cites_to_element -> 'case_ids') AS case_ids ON true
	JOIN public.cases c2 
		ON case_ids::text = c2.id
	LIMIT 10
)
SELECT create_case_link(edges.id_from, edges.id_to) 
FROM edges;

SELECT c1.id AS id_from, c2.id AS id_to
	FROM public.cases c1
	LEFT JOIN 
	    LATERAL jsonb_array_elements(c1.data -> 'cites_to') AS cites_to_element ON true
	LEFT JOIN 
	    LATERAL jsonb_array_elements(cites_to_element -> 'case_ids') AS case_ids ON true
	JOIN public.cases c2 
		ON case_ids::text = c2.id
	LIMIT 10;

WITH edges AS (
	SELECT DISTINCT c1.id AS id_from, c2.id AS id_to
	FROM public.cases c1
	LEFT JOIN 
	    LATERAL jsonb_array_elements(c1.data -> 'cites_to') AS cites_to_element ON true
	LEFT JOIN 
	    LATERAL jsonb_array_elements(cites_to_element -> 'case_ids') AS case_ids ON true
	JOIN public.cases c2 
		ON case_ids::text = c2.id
), gedges AS (
	SELECT edges.id_from, node1.id AS gid_from, edges.id_to, node2.id AS gid_to
	FROM edges
	LEFT JOIN case_graph_full."case" node1 ON node1.properties::json ->> 'case_id' = edges.id_from
	LEFT JOIN case_graph_full."case" node2 ON node2.properties::json ->> 'case_id' = edges.id_to
)
INSERT INTO case_graph_full."REF" (start_id, end_id)
SELECT gid_from AS start_id, gid_to AS end_id
FROM gedges;

SELECT * from cypher('case_graph', $$
                    MATCH ()-[r]->(n)
                    WHERE n.case_id IN ['782330', '615468']
                    RETURN r
                $$) as (r agtype);

SELECT * from cypher('case_graph_full', $$
                    MATCH ()-[r]->(n)
                    WHERE n.case_id IN ['782330', '615468']
                    RETURN r
                $$) as (r agtype);

SELECT * from cypher('case_graph', $$
                    MATCH ()-[r]->()
                    RETURN r
                $$) as (r agtype);