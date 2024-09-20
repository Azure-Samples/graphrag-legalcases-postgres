-- select azure_ai.set_setting('azure_ml.scoring_endpoint','https://reranker-demo-aml-uksouth-apheb.uksouth.inference.ml.azure.com/score');
-- select azure_ai.set_setting('azure_ml.endpoint_key', '');
select azure_ai.set_setting('azure_ml.scoring_endpoint','https://reranker-demo-aml-uksouth-ibppt.uksouth.inference.ml.azure.com/score');
select azure_ai.set_setting('azure_ml.endpoint_key', '');


SELECT jsonb_array_elements(invoke.invoke) as result
FROM azure_ml.invoke('
{"pairs": [
    ["what is panda?", "hi"], 
    ["what is panda?", "The giant panda (Ailuropoda melanoleuca), sometimes called a panda bear or simply panda, is a bear species endemic to China."]
]}', deployment_name=>'bge-reranker-large-hf-1');

SELECT data -> 'casebody' -> 'opinions' -> 0 ->> 'text' AS text, data
		FROM cases
		WHERE data ->> 'name_abbreviation'::text LIKE '%Foisy v. Wyman%';
		
-- Fused vector + pagerank results
CREATE OR REPLACE FUNCTION get_ranked_cases()
RETURNS TABLE (
	score			 NUMERIC,
    pagerank_rank    BIGINT,
    id               TEXT,
    vector_rank      BIGINT,
    abbr             TEXT,
    pagerank         NUMERIC,
    data             JSONB
) AS $$
DECLARE
	embedding VECTOR := azure_openai.create_embeddings('text-embedding-3-small', 'Water leaking into the apartment from the floor above causing damages to the property. water damage caused by negligence')::vector;
BEGIN
	RETURN QUERY
	WITH vector AS (
		SELECT cases.id, RANK() OVER (ORDER BY description_vector <=> embedding) AS vector_rank, cases.data ->> 'name_abbreviation' AS abbr, (cases.data#>>'{analysis, pagerank, percentile}')::NUMERIC AS pagerank, cases.data
		FROM cases
		ORDER BY description_vector <=> embedding
		LIMIT 100
	),
	combined AS (
		SELECT RANK() OVER (ORDER BY vector.pagerank DESC) AS pagerank_rank, vector.* FROM vector ORDER BY vector.pagerank DESC
	)
	SELECT
	    COALESCE(1.0 / (60 + combined.vector_rank), 0.0) +
	    COALESCE(1.0 / (60 + combined.pagerank_rank), 0.0) AS score,
		combined.*
	FROM combined
	ORDER BY score DESC;
END;
$$ LANGUAGE plpgsql;

SELECT * FROM get_ranked_cases();


CREATE OR REPLACE FUNCTION generate_json_pairs(query TEXT, n INT)
RETURNS jsonb AS $$
BEGIN
    RETURN (
        SELECT jsonb_build_object(
            'pairs', 
            jsonb_agg(
                jsonb_build_array(query, LEFT(text, 8000))
            )
        ) AS result_json
        FROM (
            SELECT id, data -> 'casebody' -> 'opinions' -> 0 ->> 'text' AS text
		    FROM cases
		    ORDER BY description_vector <=> azure_openai.create_embeddings('text-embedding-3-small', query)::vector
		    LIMIT n
        ) subquery
    );
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION semantic_relevance(query TEXT, n INT)
RETURNS jsonb AS $$
DECLARE
    json_pairs jsonb;
	result_json jsonb;
BEGIN
	json_pairs := generate_json_pairs(query, n);
	result_json := azure_ml.invoke(
				json_pairs,
				deployment_name=>'bge-reranker-large-hf-1',
				timeout_ms => 120000);
	RETURN (
		SELECT result_json as result
	);
END $$ LANGUAGE plpgsql;

SELECT pg_get_functiondef(p.oid)
FROM pg_proc p
WHERE proname = 'invoke';

-- Query to use semantic ranker model to rerank the results of vector search
SELECT generate_json_pairs('Water leaking into the apartment from the floor above causing damages to the property. water damage caused by negligence') AS result_json;
WITH vector AS (
	SELECT ROW_NUMBER() OVER () AS ord, text, data
	FROM (
		SELECT data -> 'casebody' -> 'opinions' -> 0 ->> 'text' AS text, data
		FROM cases
		ORDER BY description_vector <=> azure_openai.create_embeddings('text-embedding-3-small', 'Water leaking into the apartment from the floor above causing damages to the property. water damage caused by negligence')::vector
		LIMIT 5)
),
result AS (
	SELECT * 
	FROM jsonb_array_elements(
			semantic_relevance('Water leaking into the apartment from the floor above causing damages to the property. water damage caused by negligence',
			5)
		) WITH ORDINALITY AS elem(value)
)
SELECT vector.ord AS ord, result.value::DOUBLE PRECISION AS value, data->>'name_abbreviation', LEFT(vector.text, 20000), data
FROM vector
JOIN result ON vector.ord = result.ordinality
ORDER BY value DESC;

-- Ignore this - experimental
SELECT generate_json_pairs('Water leaking into the apartment from the floor above. What are the prominent legal precedents in Washington on this problem?') AS result_json;
WITH vector AS (
	SELECT ROW_NUMBER() OVER () AS ord, text
	FROM (
		SELECT data -> 'casebody' -> 'opinions' -> 0 ->> 'text' AS text
		FROM cases
		ORDER BY description_vector <=> azure_openai.create_embeddings('text-embedding-3-small', 'Water leaking into the apartment from the floor above. What are the prominent legal precedents in Washington on this problem?')::vector
		LIMIT 100)
),
result AS (
	SELECT * 
	FROM jsonb_array_elements(
			semantic_relevance('Water leaking into the apartment from the floor above. What are the prominent legal precedents in Washington on this problem?')
		) WITH ORDINALITY AS elem(value)
)
SELECT vector.ord AS ord, result.value::DOUBLE PRECISION AS value, LEFT(vector.text, 20000)
FROM vector
JOIN result ON vector.ord = result.ordinality
ORDER BY azure_openai.create_embeddings('text-embedding-3-small', LEFT(vector.text, 20000),
			1536, --dimension
			  3600000, --timeouts_ms
			  true, --throw_on_error
			  10, --max_attempts
			  10000 --retry_delay
			  )::vector <=> 
	     azure_openai.create_embeddings('text-embedding-3-small', 'Water leaking into the apartment from the floor above. What are the prominent legal precedents in Washington on this problem?',
		 	1536, --dimension
			  3600000, --timeouts_ms
			  true, --throw_on_error
			  10, --max_attempts
			  10000 --retry_delay
			  )::vector;

SELECT * 
	FROM jsonb_array_elements(
			semantic_relevance('Water leaking into the apartment from the floor above causing damages to the property. water damage caused by negligence')
		) WITH ORDINALITY AS elem(value)
ORDER BY value DESC;