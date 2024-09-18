SELECT data#>>'{casebody, opinions, 0}' 
FROM public.cases;
select azure_ai.version();

-- Setup Azure OpenAI endpoint
select azure_ai.set_setting('azure_openai.endpoint', 'https://mluk-az-open-ai.openai.azure.com/');
select azure_ai.set_setting('azure_openai.subscription_key', '');
select azure_ai.get_setting('azure_openai.endpoint');

-- Add vector - should take about 5 mins if Azure openAI and Flex are in same region
ALTER TABLE cases
ADD COLUMN description_vector vector(1536) --OPEN AI embeddings are 1536 dimensions
GENERATED ALWAYS AS (
	azure_openai.create_embeddings (
	'text-embedding-3-small', -- example deployment name in Azure OpenAI which CONTAINS text-embedding-ADA-003-small-model
	data#>>'{name}' || LEFT(data#>>'{casebody, opinions, 0}', 8000),
	1536, --dimension
	3600000, --timeouts_ms
	false, --throw_on_error
	10, --max_attempts
	1200)::vector) STORED; -- TEXT strings concatenated AND sent TO Azure OpenAI  --retry_delay

ALTER TABLE cases
ADD COLUMN description_vector vector(1536);

-- Loop to do a bulk embedding

DO $$
DECLARE
    batch_size INT := 500;  -- Adjust the batch size as needed
    offset1 INT := 0;
    rows_updated INT;
BEGIN
    LOOP
        -- Update a batch of rows
        UPDATE cases
        SET description_vector = azure_openai.create_embeddings(
            'text-embedding-3-small',  -- example deployment name in Azure OpenAI
            data#>>'{name}' || LEFT(data#>>'{casebody, opinions, 0}', 8000),
            1536,  -- dimension
            3600000,  -- timeout_ms
            false,  -- throw_on_error
            10,  -- max_attempts
            1200  -- retry_delay_ms
        )::vector
        WHERE id IN (
            SELECT id
            FROM cases
			where description_vector is null
            ORDER BY id
            LIMIT batch_size
            OFFSET offset1
        );
		

        -- Get the number of rows updated
        GET DIAGNOSTICS rows_updated = ROW_COUNT;

        -- Exit the loop if no more rows are updated
        IF rows_updated = 0 THEN
            EXIT;
        END IF;

        -- Increment the offset for the next batch
        offset1 := offset1 + batch_size;

        -- Commit the transaction to avoid long-running transactions
        COMMIT;
    END LOOP;
END $$;


SELECT description_vector FROM public.cases
where description_vector is null
ORDER BY description_vector;

