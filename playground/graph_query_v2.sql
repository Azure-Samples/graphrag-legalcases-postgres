LOAD 'age';
SET search_path = public, ag_catalog, "$user";


-- golden dataset
drop table gold_dataset;
CREATE TABLE gold_dataset (
    gold_id TEXT,
    label TEXT
);
INSERT INTO gold_dataset (gold_id, label)
VALUES
('782330', 'orig-vector'), ('615468', 'gold-graph'), ('1095193', 'gold-graph'), ('1034620', 'gold-graph'), ('772283', 'gold'), 
('1186056', 'gold-graph'), ('1127907', 'gold-graph'), ('591482', 'gold'), ('594079', 'gold-graph'), ('561149', 'gold'), 
('1086651', 'orig'), ('2601920', 'gold-graph'), ('552773', 'gold'), ('1346648', 'orig-semantic'), ('4912975', 'gold'), 
('999494', 'gold'), ('1005731', 'gold-semantic'), ('828223', 'gold'), ('4920250', 'gold'), ('4933418', 'gold'), 
('798646', 'gold'), 
-- new values
('768356', 'gold-semantic'), ('1017660', 'gold-vector'),
('4953587', 'maybe-graph'), ('630224', 'maybe-semantic'), ('481657', 'maybe-semantic'),
('634444', 'no'), ('4975399', 'no'), ('1279441', 'no'), ('1091260', 'no'), ('821843', 'no'), ('674990', 'no'), ('5041745', 'no'), ('4938756', 'no'),
-- From court of appeals
('473788', 'gold-graph-appeals'),
('3977147', 'no'), ('1352760', 'no'), ('5752736', 'no');

-- FINAL gold dataset
select * from gold_dataset
where label like 'gold-%';


SELECT jsonb_build_object(
    'pairs',
    jsonb_agg_pairs_agg('Water leaking into the apartment from the floor above.', cases.data -> 'casebody' -> 'opinions' -> 0 ->> 'text')
) AS result_json
FROM cases
limit 1;

-- FINAL QUERY
-- Recall:    40% -> 60% -> 70%
WITH
user_query as (
	select 'Water leaking into the apartment from the floor above.' as query_text
),
embedding_query AS (
    SELECT query_text, azure_openai.create_embeddings('text-embedding-3-small', query_text)::vector AS embedding
    from user_query
),
vector AS (
    SELECT cases.id, cases.data#>>'{name_abbreviation}' AS case_name, cases.data#>>'{decision_date}' AS date, cases.data AS data, 
    RANK() OVER (ORDER BY description_vector <=> embedding) AS vector_rank, query_text, embedding
    FROM cases, embedding_query
    WHERE (cases.data#>>'{court, id}')::integer IN (9029)--, 8985) -- Washington Supreme Court (9029) or Washington Court of Appeals (8985)
    ORDER BY description_vector <=> embedding
    LIMIT 60
),
json_payload AS (
    SELECT jsonb_build_object(
        'pairs', 
        jsonb_agg(
            jsonb_build_array(
                query_text, 
                LEFT(data -> 'casebody' -> 'opinions' -> 0 ->> 'text', 800)
            )
        )
    ) AS json_pairs
    FROM vector
),
semantic AS (
    SELECT elem.relevance::DOUBLE precision as relevance, elem.ordinality
    FROM json_payload,
         LATERAL jsonb_array_elements(
             azure_ml.invoke(
                 json_pairs,
                 deployment_name => 'bge-v2-m3-1',
                 timeout_ms => 180000
             )
         ) WITH ORDINALITY AS elem(relevance)
),
semantic_ranked AS (
    SELECT RANK() OVER (ORDER BY relevance DESC) AS semantic_rank,
			semantic.*, vector.*
    FROM vector
    JOIN semantic ON vector.vector_rank = semantic.ordinality
    ORDER BY semantic.relevance DESC
),
graph AS (
	select id, COUNT(ref_id) AS refs
	from (
	    SELECT semantic_ranked.id, graph_query.ref_id, c2.description_vector <=> embedding AS ref_cosine
		FROM semantic_ranked
		LEFT JOIN cypher('case_graph', $$
	            MATCH (s)-[r:REF]->(n)
	            RETURN n.case_id AS case_id, s.case_id AS ref_id
	        $$) as graph_query(case_id TEXT, ref_id TEXT)
		ON semantic_ranked.id = graph_query.case_id
		LEFT JOIN cases c2
		ON c2.id = graph_query.ref_id
		WHERE semantic_ranked.semantic_rank <= 25
		ORDER BY ref_cosine
		LIMIT 200
	)
	group by id
),
graph2 as (
	select semantic_ranked.*, graph.refs 
	from semantic_ranked
	left join graph
	on semantic_ranked.id = graph.id
),
graph_ranked AS (
    SELECT RANK() OVER (ORDER BY COALESCE(graph2.refs, 0) DESC) AS graph_rank, graph2.*
    FROM graph2 ORDER BY graph_rank DESC
),
rrf AS (
    select
    	gold_dataset.label,
        COALESCE(1.0 / (60 + graph_ranked.graph_rank), 0.0) +
        COALESCE(1.0 / (60 + graph_ranked.semantic_rank), 0.0) AS score,
        graph_ranked.*
    FROM graph_ranked
	left join gold_dataset
	on id = gold_id
    ORDER BY score DESC
)
select label,score,graph_rank,semantic_rank,vector_rank,id,case_name,"date","data",refs,relevance
FROM rrf
order by score DESC;


-- Demo dataset
WITH
user_query as (
	select 'Water leaking into the apartment from the floor above.' as query_text
),
embedding_query AS (
    SELECT query_text, azure_openai.create_embeddings('text-embedding-3-small', query_text)::vector AS embedding
    from user_query
),
vector AS (
    SELECT cases.id, cases.data#>>'{name_abbreviation}' AS case_name, cases.data#>>'{decision_date}' AS date, cases.data AS data, 
    RANK() OVER (ORDER BY description_vector <=> embedding) AS vector_rank, query_text, embedding
    FROM cases, embedding_query
    WHERE (cases.data#>>'{court, id}')::integer IN (9029)--, 8985) -- Washington Supreme Court (9029) or Washington Court of Appeals (8985)
    ORDER BY description_vector <=> embedding
    LIMIT 60
),
graph AS (
    SELECT vector.id, graph_query.ref_id
	FROM vector
	LEFT JOIN cypher('case_graph', $$
            MATCH (s)-[r:REF]->(n)
            RETURN n.case_id AS case_id, s.case_id AS ref_id
        $$) as graph_query(case_id TEXT, ref_id TEXT)
	ON vector.id = graph_query.case_id
)
select * from graph;

-- Unoptimized final query
-- Recall:    40% -> 60% -> 70%
WITH
embedding_query AS (
    SELECT azure_openai.create_embeddings('text-embedding-3-small', 'Water leaking into the apartment from the floor above.')::vector AS embedding
),
vector AS (
    SELECT cases.id, cases.data#>>'{name_abbreviation}' AS case_name, cases.data#>>'{decision_date}' AS date, cases.data AS data, 
    RANK() OVER (ORDER BY description_vector <=> embedding) AS vector_rank, embedding
    FROM cases, embedding_query
    WHERE (cases.data#>>'{court, id}')::integer IN (9029)--, 8985) -- Washington Supreme Court (9029) or Washington Court of Appeals (8985)
    ORDER BY description_vector <=> embedding
    LIMIT 60
),
semantic AS (
    SELECT get_relevance('Water leaking into the apartment from the floor above.', 
		  		vector.data -> 'casebody' -> 'opinions' -> 0 ->> 'text') AS relevance,
		   vector.*
    FROM vector
),
semantic_ranked AS (
    SELECT RANK() OVER (ORDER BY relevance DESC) AS semantic_rank,
		   semantic.*
    FROM semantic
    ORDER BY semantic.relevance DESC
),
graph AS (
	select id, COUNT(ref_id) AS refs
	from (
	    SELECT semantic_ranked.id, graph_query.ref_id, c2.description_vector <=> embedding AS ref_cosine
		FROM semantic_ranked
		LEFT JOIN cypher('case_graph_full', $$
	            MATCH (s)-[r]->(n)
	            RETURN n.case_id AS case_id, s.case_id AS ref_id
	        $$) as graph_query(case_id TEXT, ref_id TEXT)
		ON semantic_ranked.id = graph_query.case_id
		LEFT JOIN cases c2
		ON c2.id = graph_query.ref_id
		WHERE semantic_ranked.semantic_rank <= 25
		ORDER BY ref_cosine
		LIMIT 200
	)
	group by id
),
graph2 as (
	select semantic_ranked.*, graph.refs 
	from semantic_ranked
	left join graph
	on semantic_ranked.id = graph.id
),
graph_ranked AS (
    SELECT RANK() OVER (ORDER BY COALESCE(graph2.refs, 0) DESC) AS graph_rank, graph2.*
    FROM graph2 ORDER BY graph_rank DESC
),
rrf AS (
    select
    	gold_dataset.label,
        COALESCE(1.0 / (60 + graph_ranked.graph_rank), 0.0) +
        COALESCE(1.0 / (60 + graph_ranked.semantic_rank), 0.0) AS score,
        graph_ranked.*
    FROM graph_ranked
	left join gold_dataset
	on id = gold_id
    ORDER BY score DESC
)
SELECT * 
FROM rrf
order by score DESC;


drop table t1;
CREATE TABLE t1 AS (
WITH
embedding_query AS (
    SELECT azure_openai.create_embeddings('text-embedding-3-small', 'Water leaking into the apartment from the floor above.')::vector AS embedding
),
vector AS (
    SELECT cases.id, cases.data#>>'{name_abbreviation}' AS case_name, cases.data#>>'{decision_date}' AS date, cases.data AS data, RANK() OVER (ORDER BY description_vector <=> embedding) AS vector_rank
    FROM cases, embedding_query
    WHERE (cases.data#>>'{court, id}')::integer IN (9029)--, 8985) -- Washington Supreme Court (9029) or Washington Court of Appeals (8985)
		  --AND cases.data#>>'{decision_date}' > '2009'
    ORDER BY description_vector <=> embedding
    LIMIT 60
),
semantic AS (
    SELECT get_relevance('Water leaking into the apartment from the floor above.', 
		  		vector.data -> 'casebody' -> 'opinions' -> 0 ->> 'text') AS relevance,
		   vector.*
    FROM vector
),
semantic_ranked AS (
    SELECT RANK() OVER (ORDER BY relevance DESC) AS semantic_rank,
		   semantic.*
    FROM semantic
    ORDER BY semantic.relevance DESC
),
graph AS (
    SELECT graph_query.ref_id, semantic_ranked.*, c2.data -> 'casebody' -> 'opinions' -> 0 ->> 'text' AS ref_text
	FROM semantic_ranked
	LEFT JOIN cypher('case_graph_full', $$
            MATCH (s)-[r]->(n)
            RETURN n.case_id AS case_id, s.case_id AS ref_id
        $$) as graph_query(case_id TEXT, ref_id TEXT)
	ON semantic_ranked.id = graph_query.case_id
	LEFT JOIN cases c2
	ON c2.id = graph_query.ref_id
)
select get_relevance('Water leaking into the apartment from the floor above.', ref_text) AS ref_rel, * from graph);



-- (Precursor to final) Vector search based check of refs, 7/10, 8/20: 
-- Recall:    40% -> 60% -> 70%
WITH embedding_query AS (
    SELECT azure_openai.create_embeddings('text-embedding-3-small', 'Water leaking into the apartment from the floor above.')::vector AS embedding
),
graph AS (
	select id, AVG(ref_rel) avg_ref_rel, COUNT(ref_id) AS refs
	from (
		SELECT c2.description_vector <=> embedding_query.embedding AS ref_cosine,
		       t1.*
		FROM t1
		JOIN embedding_query ON true
		LEFT JOIN cases c2 ON t1.ref_id = c2.id
		WHERE t1.semantic_rank <= 25
		ORDER BY ref_cosine
		LIMIT 200
	)
	group by id
),
graph2 AS (
	select t1.id, case_name, date,
			semantic_rank,vector_rank, relevance,"data"
	from t1
	group by t1.id, case_name, date, semantic_rank,vector_rank,relevance,"data"
),
graph3 as (
	select graph2.*, graph.refs from graph2
	left join graph
	on graph.id = graph2.id
),
graph_ranked AS (
    SELECT RANK() OVER (ORDER BY COALESCE(graph3.refs, 0) DESC) AS graph_rank, graph3.*
    FROM graph3 ORDER BY graph_rank DESC
),
rrf AS (
    select
    	gold_dataset.label,
        COALESCE(1.0 / (60 + graph_ranked.graph_rank), 0.0) +
        COALESCE(1.0 / (60 + graph_ranked.semantic_rank), 0.0) AS score,
        graph_ranked.*
    FROM graph_ranked
	left join gold_dataset
	on id = gold_id
    ORDER BY score DESC
)
SELECT * 
FROM rrf
order by score DESC;

-- Experiments



select * 
from cypher('case_graph_full', $$
            MATCH (s)-[r]->(n)
			WHERE n.case_id = '1127907'
            RETURN n.case_id AS case_id, s.case_id AS ref_id
        $$) as graph_query(case_id TEXT, ref_id TEXT);

-- 6/10, 10/20
WITH
graph AS (
	select id, label, case_name, date,
			AVG(ref_rel) avg_ref_rel, COUNT(ref_id) AS refs,
			semantic_rank,relevance,"data",vector_rank
	from (
		select t1.*, gold_dataset.label from t1
		left join gold_dataset
		on id = gold_id
		where semantic_rank <= 50
		order by ref_rel desc
		limit 200
	)
	group by id, label, case_name, date,semantic_rank,relevance,"data",vector_rank
),
graph_ranked AS (
    SELECT RANK() OVER (ORDER BY COALESCE(graph.refs, 0) DESC) AS graph_rank, graph.*
    FROM graph ORDER BY graph_rank DESC
)
SELECT * FROM graph_ranked
order by graph_ranked;

-- 8/10, 10/19, 19 total
WITH
graph AS (
	select id, label, case_name, date,
			AVG(ref_rel) avg_ref_rel, COUNT(ref_id) AS refs,
			semantic_rank,relevance,"data",vector_rank
	from (
		select t1.*, gold_dataset.label from t1
		left join gold_dataset
		on id = gold_id
		where semantic_rank <= 20
		order by ref_rel desc
		limit 100
	)
	group by id, label, case_name, date,semantic_rank,relevance,"data",vector_rank
),
graph_ranked AS (
    SELECT RANK() OVER (ORDER BY COALESCE(graph.refs, 0) DESC) AS graph_rank, graph.*
    FROM graph ORDER BY graph_rank DESC
),
rrf AS (
    SELECT
        COALESCE(1.0 / (60 + graph_ranked.graph_rank), 0.0) +
        COALESCE(1.0 / (60 + graph_ranked.semantic_rank), 0.0) AS score,
        graph_ranked.*
    FROM graph_ranked
    ORDER BY score DESC
)
SELECT * 
FROM rrf;

-- 7/10, 9/20: 40% -> 60% -> 70%
WITH
graph AS (
	select id, AVG(ref_rel) avg_ref_rel, COUNT(ref_id) AS refs
	from (
		select t1.* from t1
		where semantic_rank <= 20
		order by ref_rel desc
		limit 100
	)
	group by id
),
graph2 AS (
	select t1.id, case_name, date,
			semantic_rank,vector_rank, relevance,"data"
	from t1
	group by t1.id, case_name, date, semantic_rank,vector_rank,relevance,"data"
),
graph3 as (
	select graph2.*, graph.refs from graph2
	left join graph
	on graph.id = graph2.id
),
graph_ranked AS (
    SELECT RANK() OVER (ORDER BY COALESCE(graph3.refs, 0) DESC) AS graph_rank, graph3.*
    FROM graph3 ORDER BY graph_rank DESC
),
rrf AS (
    select
    	gold_dataset.label,
        COALESCE(1.0 / (60 + graph_ranked.graph_rank), 0.0) +
        COALESCE(1.0 / (60 + graph_ranked.semantic_rank), 0.0) AS score,
        graph_ranked.*
    FROM graph_ranked
	left join gold_dataset
	on id = gold_id
    ORDER BY score DESC
)
SELECT * 
FROM rrf
order by score DESC;


with t2 as (
	select RANK() OVER (ORDER BY ref_rel DESC) AS ref_sem_rank, cases.data#>>'{court, name}' AS ref_court, cases.data as ref_data, t1.*
	from t1
	left join cases
	on ref_id = cases.id
)
select gold_dataset.label, t2.* from t2
left join gold_dataset
on ref_id = gold_id
where id IN ('1186056', '1127907', '4975399')
order by id, ref_rel desc;

WITH
embedding_query AS (
    SELECT azure_openai.create_embeddings('text-embedding-3-small', 'Water leaking into the apartment from the floor above.')::vector AS embedding
)
SELECT cases.id, description_vector <=> embedding as cosine, cases.data#>>'{name_abbreviation}' AS case_name, cases.data#>>'{decision_date}' AS date, cases.data AS data, RANK() OVER (ORDER BY description_vector <=> embedding) AS vector_rank
    FROM cases, embedding_query
    WHERE (cases.data#>>'{court, id}')::integer IN (9029)--, 8985) -- Washington Supreme Court (9029) or Washington Court of Appeals (8985)
		  --AND cases.data#>>'{decision_date}' > '2009'
    	  --and id = '1199192'
    ORDER BY description_vector <=> embedding
    offset 2000
   	limit 10;

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


-- regular search only within last 7 years - doesn't look too good
WITH
embedding_query AS (
    SELECT azure_openai.create_embeddings('text-embedding-3-small', 'Water leaking into the apartment from the floor above.')::vector AS embedding
),
vector AS (
    SELECT cases.id, cases.data#>>'{name_abbreviation}' AS case_name, cases.data#>>'{decision_date}' AS date, cases.data AS data, RANK() OVER (ORDER BY description_vector <=> embedding) AS vector_rank
    FROM cases, embedding_query
    WHERE (cases.data#>>'{court, id}')::integer IN (9029)--, 8985) -- Washington Supreme Court (9029) or Washington Court of Appeals (8985)
		  --AND cases.data#>>'{decision_date}' > '2009'
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
    SELECT graph_query.refs, semantic_ranked.vector_rank, semantic_ranked.*, graph_query.case_id from semantic_ranked
	LEFT JOIN cypher('case_graph_full', $$
            MATCH ()-[r]->(n)
            RETURN n.case_id, COUNT(r) AS refs
        $$) as graph_query(case_id TEXT, refs BIGINT)
	ON semantic_ranked.id = graph_query.case_id
),
graph_ranked AS (
    SELECT RANK() OVER (ORDER BY COALESCE(graph.refs, 0) DESC) AS graph_rank, graph.*
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

-- Drafts
SELECT MAX(cases.data#>>'{decision_date}') FROM cases;
SELECT cases.data#>>'{decision_date}' AS date FROM cases WHERE cases.data#>>'{decision_date}' > '2009' ORDER BY date LIMIT 10;