-- Vector query
WITH 
embedding_query AS (
    SELECT azure_openai.create_embeddings('text-embedding-3-small', 
    					'Water leaking into the apartment from the floor above.')::vector AS embedding
),
vector_similarity AS (
    SELECT cases.id, cases.data#>>'{name_abbreviation}' AS case_name, 
    	   cases.data#>>'{decision_date}' AS date,
    	   cases.data#>>'{casebody, opinions, 0, text}' AS case_text
    FROM cases, embedding_query
    WHERE (cases.data#>>'{court, id}')::integer IN (9029) -- Washington Supreme Court (9029)
    ORDER BY description_vector <=> embedding
    LIMIT 60
)
SELECT * FROM vector_similarity LIMIT 60;