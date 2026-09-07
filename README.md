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

## Ingestion guarantees

A file hash is unique at the database level. Document creation, all chunk
inserts, and the transition to `completed` occur in one transaction. A failure
rolls the transaction back, so an incomplete upload cannot later be returned as
an indexed duplicate. Concurrent uploads of the same file converge on the same
completed document.
