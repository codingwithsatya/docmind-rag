from pathlib import Path
import re


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "migrations"
    / "002_upgrade_legacy_schema.sql"
)
INITIAL_MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "migrations"
    / "001_initial_schema.sql"
)


def migration_sql():
    return MIGRATION_PATH.read_text(encoding="utf-8")


def normalized_sql():
    return " ".join(migration_sql().lower().split())


def normalized_initial_sql():
    return " ".join(
        INITIAL_MIGRATION_PATH.read_text(encoding="utf-8").lower().split()
    )


def test_migration_is_additive_and_transactional():
    sql = normalized_sql()

    assert sql.startswith("begin;")
    assert sql.endswith("commit;")
    assert "create table" not in sql
    assert "drop table" not in sql
    assert "truncate " not in sql
    assert "delete from" not in sql
    assert "update public.document_chunks" not in sql


def test_migration_backfills_only_new_document_metadata():
    sql = normalized_sql()

    assert "add column if not exists ingestion_status text" in sql
    assert "add column if not exists completed_at timestamptz" in sql
    assert "ingestion_status = 'completed'" in sql
    assert "ingestion_status = 'failed'" in sql
    assert "and exists ( select 1 from public.document_chunks" in sql
    assert "and not exists ( select 1 from public.document_chunks" in sql
    assert "alter column file_hash set not null" in sql
    assert "alter column ingestion_status set default 'processing'" in sql
    assert "alter column ingestion_status set not null" in sql
    assert "alter column page_number set not null" in sql

    updated_tables = re.findall(r"\bupdate\s+public\.([a-z_]+)", sql)
    assert updated_tables == ["documents", "documents"]


def test_migration_adds_required_constraints_and_indexes():
    sql = normalized_sql()

    required_names = {
        "documents_ingestion_status_valid",
        "documents_completion_consistent",
        "document_chunks_document_chunk_unique",
        "document_chunks_chunk_index_nonnegative",
        "document_chunks_page_number_positive",
        "document_chunks_content_not_empty",
        "document_chunks_document_id_idx",
        "document_chunks_embedding_hnsw_idx",
        "document_chunks_content_fts_idx",
    }

    for name in required_names:
        assert name in sql

    assert "unique (document_id, chunk_index)" in sql
    assert "check (chunk_index >= 0)" in sql
    assert "check (page_number > 0)" in sql
    assert "check (length(btrim(content)) > 0)" in sql
    assert "using hnsw (embedding vector_cosine_ops)" in sql
    assert "using gin (to_tsvector('english', content))" in sql


def test_migration_guards_repeatable_schema_operations():
    sql = normalized_sql()

    assert sql.count("add column if not exists") == 2
    assert sql.count("if not exists ( select 1 from pg_catalog.pg_constraint") == 6
    assert sql.count("create index if not exists") == 3


def test_migration_has_bounded_timeouts_and_locked_preflights():
    sql = normalized_sql()

    lock_position = sql.index(
        "lock table public.documents, public.document_chunks"
    )
    first_preflight_position = sql.index("where file_hash is null")
    first_schema_change_position = sql.index("alter table public.documents")

    assert "set local lock_timeout = '5s'" in sql
    assert "set local statement_timeout = '15min'" in sql
    assert lock_position < first_preflight_position < first_schema_change_position
    assert "where file_hash is null" in sql
    assert "where page_number is null or page_number <= 0" in sql
    assert "where chunk_index < 0" in sql
    assert "where content is null or length(btrim(content)) = 0" in sql
    assert "group by document_id, chunk_index having count(*) > 1" in sql
    assert sql.count("raise exception 'migration 002 preflight failed:") == 5


def test_application_tables_are_schema_qualified():
    sql = normalized_sql()

    forbidden_unqualified_references = {
        "alter table documents",
        "alter table document_chunks",
        "update documents",
        "update document_chunks",
        "from documents",
        "from document_chunks",
        "on document_chunks",
        "lock table documents",
    }

    for reference in forbidden_unqualified_references:
        assert reference not in sql

    assert "on public.document_chunks (document_id)" in sql
    assert "on public.document_chunks using hnsw" in sql
    assert "on public.document_chunks using gin" in sql


def test_legacy_upgrade_matches_initial_application_contract():
    initial_sql = normalized_initial_sql()
    upgrade_sql = normalized_sql()

    shared_constraints_and_indexes = {
        "documents_ingestion_status_valid",
        "documents_completion_consistent",
        "document_chunks_document_chunk_unique",
        "document_chunks_chunk_index_nonnegative",
        "document_chunks_page_number_positive",
        "document_chunks_content_not_empty",
        "document_chunks_document_id_idx",
        "document_chunks_embedding_hnsw_idx",
        "document_chunks_content_fts_idx",
    }

    for schema_object in shared_constraints_and_indexes:
        assert schema_object in initial_sql
        assert schema_object in upgrade_sql

    assert "file_hash text not null" in initial_sql
    assert "alter column file_hash set not null" in upgrade_sql
    assert "ingestion_status text not null default 'processing'" in initial_sql
    assert "alter column ingestion_status set default 'processing'" in upgrade_sql
    assert "alter column ingestion_status set not null" in upgrade_sql
    assert "completed_at timestamptz" in initial_sql
    assert "add column if not exists completed_at timestamptz" in upgrade_sql
    assert "page_number integer not null" in initial_sql
    assert "alter column page_number set not null" in upgrade_sql
    assert "using hnsw (embedding vector_cosine_ops)" in initial_sql
    assert "using hnsw (embedding vector_cosine_ops)" in upgrade_sql
