DO $$
DECLARE
    batch_size INT := 500;  -- Adjust the batch size as needed
    offset1 INT := 0;
    rows_updated INT;
BEGIN
    LOOP
        -- Update a batch of rows
        RAISE NOTICE 'We are at the % offset', offset1 ;
        UPDATE cases SET description_vector = azure_openai.create_embeddings(
            'text-embedding-3-small',  -- example deployment name in Azure OpenAI
            COALESCE(data#>>'{name}', 'default_value') || COALESCE(LEFT(data#>>'{casebody, opinions, 0}', 8000), 'default_value'),
            1536,  -- dimension
            3600000,  -- timeout_ms
            false,  -- throw_on_error
            10,  -- max_attempts
            2000  -- retry_delay_ms
        )::vector
        WHERE id IN (
            SELECT id
            FROM cases
			where description_vector is null
            ORDER BY id ASC
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
