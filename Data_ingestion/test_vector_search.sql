SELECT opinions_text FROM public.cases_playground
LIMIT 100;

-- array_to_string(ARRAY(SELECT jsonb_path_query(data, '$.casebody.opinions[*].text')),

-- And search with vector column
-- Search with vector column
SELECT 
    array_to_string(
        ARRAY(
            SELECT jsonb_path_query(data, '$.casebody.opinions[*].text')
        ), 
        ', '
    ) AS opinion_texts,  
    description_vector <=> azure_openai.create_embeddings(
        'text-embedding-3-small', 
        'leaking pipes in my house and favourable judgement'
    )::vector AS distance
FROM public.cases
ORDER BY distance
LIMIT 5;


