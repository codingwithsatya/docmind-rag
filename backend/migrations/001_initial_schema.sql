BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    ingestion_status TEXT NOT NULL DEFAULT 'processing',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    CONSTRAINT documents_file_hash_unique UNIQUE (file_hash),
    CONSTRAINT documents_ingestion_status_valid CHECK (
        ingestion_status IN ('processing', 'completed', 'failed')
    ),
    CONSTRAINT documents_completion_consistent CHECK (
        (ingestion_status = 'completed' AND completed_at IS NOT NULL)
        OR (ingestion_status <> 'completed' AND completed_at IS NULL)
    )
);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT document_chunks_document_fk
        FOREIGN KEY (document_id)
        REFERENCES documents (id)
        ON DELETE CASCADE,
    CONSTRAINT document_chunks_document_chunk_unique
        UNIQUE (document_id, chunk_index),
    CONSTRAINT document_chunks_chunk_index_nonnegative
        CHECK (chunk_index >= 0),
    CONSTRAINT document_chunks_page_number_positive
        CHECK (page_number > 0),
    CONSTRAINT document_chunks_content_not_empty
        CHECK (length(btrim(content)) > 0)
);

CREATE INDEX document_chunks_document_id_idx
    ON document_chunks (document_id);

CREATE INDEX document_chunks_embedding_hnsw_idx
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX document_chunks_content_fts_idx
    ON document_chunks
    USING gin (to_tsvector('english', content));

COMMIT;
