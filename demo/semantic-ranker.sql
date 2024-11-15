WITH
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
    FROM vector_similarity
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
			semantic.*, vector_similarity.*
    FROM vector_similarity
    JOIN semantic ON vector_similarity.vector_rank = semantic.ordinality
    ORDER BY semantic.relevance DESC
)
SELECT semantic_rank,relevance,id,case_name,date FROM semantic_ranked;
