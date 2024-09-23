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
