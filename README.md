# DocMind-RAG

DocMind-RAG is a local PDF question-answering application. The FastAPI backend
extracts and chunks PDF text, stores OpenAI embeddings in PostgreSQL with
pgvector, and returns grounded answers with page-level sources. The Next.js
frontend provides the upload and chat interface.

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 15+ with the pgvector extension available
- An OpenAI API key

## Database setup

Create an empty PostgreSQL database and apply migrations in filename order:

```bash
psql postgresql://docmind:docmind@localhost:5432/docmind \
  -v ON_ERROR_STOP=1 \
  -f backend/migrations/001_initial_schema.sql
```

The initial migration enables `vector` and `pgcrypto`, creates the document and
chunk tables, fixes embeddings at 1536 dimensions, and installs uniqueness,
foreign-key, vector, and full-text-search indexes. The database user applying
the migration must be permitted to create extensions.

### Upgrading the confirmed legacy Supabase schema

Do not apply migration 001 to a database where `documents` and
`document_chunks` already exist. After taking a database backup and running the
documented preflight checks, apply only the additive legacy upgrade:

```bash
psql "$DATABASE_URL" \
  -v ON_ERROR_STOP=1 \
  -f backend/migrations/002_upgrade_legacy_schema.sql
```

Migration 002 uses a 5-second `lock_timeout`: if active traffic prevents it
from acquiring its write-blocking table lock promptly, it fails instead of
waiting indefinitely. Each statement has a 15-minute `statement_timeout`.
Schedule it during a quiet period. It preserves all document and chunk content:
documents with chunks are marked `completed`, documents without chunks are
marked `failed`, and only the new ingestion metadata is backfilled.

The HNSW and full-text indexes are deliberately built inside the transaction
while writes are locked, preserving all-or-nothing migration behavior. On a
large chunk table, either build can approach the statement timeout and blocks
writes until it finishes or the transaction rolls back. Measure table size and
index-build time before applying; increase the bounded statement timeout if
needed. Building indexes with `CREATE INDEX CONCURRENTLY` would reduce write
blocking, but PostgreSQL does not allow that command inside this transaction and
would require a separately managed, non-atomic migration.

Verify the result with read-only catalog queries:

```sql
SELECT table_name, column_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('documents', 'document_chunks')
  AND column_name IN ('ingestion_status', 'completed_at')
ORDER BY table_name, column_name;

SELECT conrelid::regclass AS table_name, conname,
       pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid IN ('public.documents'::regclass,
                   'public.document_chunks'::regclass)
ORDER BY table_name, conname;

SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('documents', 'document_chunks')
ORDER BY tablename, indexname;

SELECT format_type(atttypid, atttypmod) AS embedding_type
FROM pg_attribute
WHERE attrelid = 'public.document_chunks'::regclass
  AND attname = 'embedding'
  AND NOT attisdropped;

SELECT ingestion_status, count(*)
FROM documents
GROUP BY ingestion_status
ORDER BY ingestion_status;
```

If migration 002 fails before `COMMIT`, PostgreSQL rolls back the complete
transaction automatically. After a successful commit, prefer restoring the
pre-migration backup if rollback is necessary. A manual schema rollback may
drop the three new indexes, the six new constraints, and finally the two new
columns, but dropping the columns permanently removes their status metadata.
It does not restore application compatibility by itself, so roll back the
application and schema together. Never remove constraints until the application
has stopped relying on them.

## Backend

From the repository root:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
cp .env.example .env
backend/.venv/bin/uvicorn app.main:app --app-dir backend --reload
```

Set real values in `.env`; never commit that file. The API runs at
`http://127.0.0.1:8000`. Check the database with
`GET http://127.0.0.1:8000/health/database`.

PDF uploads default to a maximum of 10 MiB and 100 pages. Override
`MAX_PDF_UPLOAD_BYTES` or `MAX_PDF_PAGES` in `.env` with positive integers when
different limits are appropriate for your deployment.

## Frontend

In another terminal:

```bash
cd frontend
npm ci
printf 'NEXT_PUBLIC_API_URL=http://127.0.0.1:8000\n' > .env.local
npm run dev
```

Open `http://localhost:3000`.

## Verification

The focused tests use fakes and mocks; they do not connect to PostgreSQL or
OpenAI and do not require credentials.

```bash
source backend/.venv/bin/activate
cd backend
python -m pytest -q
cd ..
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m compileall -q backend/app backend/tests
cd frontend && npm run lint && npx tsc --noEmit
```

If `pytest` appears to use the wrong environment, verify the active Python
before running it:

```bash
python -c "import sys; print(sys.executable)"
```

The printed path should end in `backend/.venv/bin/python`. Using
`python -m pytest` ensures pytest runs with that same interpreter. Pytest is
configured in `backend/pytest.ini` to collect only `backend/tests`; the manual
evaluation programs under `backend/evals` are intentionally excluded.

The frontend currently has no component-test runner or DOM test environment.
Adding frontend unit tests cleanly would require choosing and configuring a
runner such as Vitest, React Testing Library, and jsdom. For now, frontend error
handling is checked by ESLint and TypeScript, while the API error contracts are
covered by backend tests.

## Ingestion guarantees

A file hash is unique at the database level. Document creation, all chunk
inserts, and the transition to `completed` occur in one transaction. A failure
rolls the transaction back, so an incomplete upload cannot later be returned as
an indexed duplicate. Concurrent uploads of the same file converge on the same
completed document.
