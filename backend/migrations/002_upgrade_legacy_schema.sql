BEGIN;

-- Fail rather than wait indefinitely for active application writes. Each
-- individual statement also has a bounded runtime within this transaction.
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '15min';

-- Keep the preflight assumptions stable while data is backfilled and schema
-- objects are built.
LOCK TABLE public.documents, public.document_chunks
    IN SHARE ROW EXCLUSIVE MODE;

-- Do not repair conflicting legacy data implicitly. Abort with a targeted
-- message so an operator can inspect and resolve it deliberately.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM public.documents
        WHERE file_hash IS NULL
    ) THEN
        RAISE EXCEPTION
            'Migration 002 preflight failed: documents.file_hash contains NULL values.';
    END IF;
END
$$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM public.document_chunks
        WHERE page_number IS NULL OR page_number <= 0
    ) THEN
        RAISE EXCEPTION
            'Migration 002 preflight failed: document_chunks.page_number contains NULL or nonpositive values.';
    END IF;
END
$$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM public.document_chunks
        WHERE chunk_index < 0
    ) THEN
        RAISE EXCEPTION
            'Migration 002 preflight failed: document_chunks.chunk_index contains negative values.';
    END IF;
END
$$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM public.document_chunks
        WHERE content IS NULL OR length(btrim(content)) = 0
    ) THEN
        RAISE EXCEPTION
            'Migration 002 preflight failed: document_chunks.content contains NULL or empty values.';
    END IF;
END
$$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM public.document_chunks
        GROUP BY document_id, chunk_index
        HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION
            'Migration 002 preflight failed: duplicate document_id/chunk_index values exist.';
    END IF;
END
$$;

ALTER TABLE public.documents
    ADD COLUMN IF NOT EXISTS ingestion_status TEXT,
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

-- Legacy documents that own at least one chunk were usable before statuses
-- existed, so preserve them as completed.
UPDATE public.documents AS document
SET
    ingestion_status = 'completed',
    completed_at = COALESCE(
        document.completed_at,
        document.created_at,
        CURRENT_TIMESTAMP
    )
WHERE
    document.ingestion_status IS NULL
    AND EXISTS (
        SELECT 1
        FROM public.document_chunks AS chunk
        WHERE chunk.document_id = document.id
    );

-- A legacy document with no chunks cannot answer questions and must not be
-- exposed as completed.
UPDATE public.documents AS document
SET
    ingestion_status = 'failed',
    completed_at = NULL
WHERE
    document.ingestion_status IS NULL
    AND NOT EXISTS (
        SELECT 1
        FROM public.document_chunks AS chunk
        WHERE chunk.document_id = document.id
    );

ALTER TABLE public.documents
    ALTER COLUMN file_hash SET NOT NULL,
    ALTER COLUMN ingestion_status SET DEFAULT 'processing',
    ALTER COLUMN ingestion_status SET NOT NULL;

ALTER TABLE public.document_chunks
    ALTER COLUMN page_number SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_constraint
        WHERE
            conrelid = 'public.documents'::regclass
            AND conname = 'documents_ingestion_status_valid'
    ) THEN
        ALTER TABLE public.documents
            ADD CONSTRAINT documents_ingestion_status_valid
            CHECK (ingestion_status IN ('processing', 'completed', 'failed'))
            NOT VALID;
    END IF;
END
$$;

ALTER TABLE public.documents
    VALIDATE CONSTRAINT documents_ingestion_status_valid;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_constraint
        WHERE
            conrelid = 'public.documents'::regclass
            AND conname = 'documents_completion_consistent'
    ) THEN
        ALTER TABLE public.documents
            ADD CONSTRAINT documents_completion_consistent
            CHECK (
                (ingestion_status = 'completed' AND completed_at IS NOT NULL)
                OR (ingestion_status <> 'completed' AND completed_at IS NULL)
            )
            NOT VALID;
    END IF;
END
$$;

ALTER TABLE public.documents
    VALIDATE CONSTRAINT documents_completion_consistent;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_constraint
        WHERE
            conrelid = 'public.document_chunks'::regclass
            AND conname = 'document_chunks_document_chunk_unique'
    ) THEN
        ALTER TABLE public.document_chunks
            ADD CONSTRAINT document_chunks_document_chunk_unique
            UNIQUE (document_id, chunk_index);
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_constraint
        WHERE
            conrelid = 'public.document_chunks'::regclass
            AND conname = 'document_chunks_chunk_index_nonnegative'
    ) THEN
        ALTER TABLE public.document_chunks
            ADD CONSTRAINT document_chunks_chunk_index_nonnegative
            CHECK (chunk_index >= 0)
            NOT VALID;
    END IF;
END
$$;

ALTER TABLE public.document_chunks
    VALIDATE CONSTRAINT document_chunks_chunk_index_nonnegative;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_constraint
        WHERE
            conrelid = 'public.document_chunks'::regclass
            AND conname = 'document_chunks_page_number_positive'
    ) THEN
        ALTER TABLE public.document_chunks
            ADD CONSTRAINT document_chunks_page_number_positive
            CHECK (page_number > 0)
            NOT VALID;
    END IF;
END
$$;

ALTER TABLE public.document_chunks
    VALIDATE CONSTRAINT document_chunks_page_number_positive;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_constraint
        WHERE
            conrelid = 'public.document_chunks'::regclass
            AND conname = 'document_chunks_content_not_empty'
    ) THEN
        ALTER TABLE public.document_chunks
            ADD CONSTRAINT document_chunks_content_not_empty
            CHECK (length(btrim(content)) > 0)
            NOT VALID;
    END IF;
END
$$;

ALTER TABLE public.document_chunks
    VALIDATE CONSTRAINT document_chunks_content_not_empty;

-- PostgreSQL creates each index in the schema of its public.document_chunks
-- parent and does not permit a separately schema-qualified index name here.
CREATE INDEX IF NOT EXISTS document_chunks_document_id_idx
    ON public.document_chunks (document_id);

CREATE INDEX IF NOT EXISTS document_chunks_embedding_hnsw_idx
    ON public.document_chunks
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS document_chunks_content_fts_idx
    ON public.document_chunks
    USING gin (to_tsvector('english', content));

COMMIT;
