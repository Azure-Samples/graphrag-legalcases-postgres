LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- search
SELECT * from cypher('graph_name', $$
            MATCH (n:label)
            RETURN n
        $$) as (n agtype);


SELECT * from cypher('graph_name', $$
            MATCH (n {property:"Node B"})
            RETURN n
        $$) as (n agtype);

SELECT * from cypher('graph_name', $$
            MATCH ()-[r]->(n {property:"Node A"})
            RETURN COUNT(r) AS refs
        $$) as (refs BIGINT);

SELECT * from cypher('graph_name', $$
            MATCH ()-[r]->(n)
			WHERE n.property IN ["Node A", "Node B"]
            RETURN n.property, COUNT(r) AS refs
        $$) as (node TEXT, refs BIGINT);

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
