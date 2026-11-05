# DocMind-RAG Architecture

Status: Proposed multi-document architecture
Last reviewed: 2026-11-05

## 1. Product goal

Allow users to upload PDFs once and query their authorized
document library without repeatedly uploading or manually selecting
individual documents.

Support document-specific questions, library-wide questions,
and grounded cross-document comparisons.

## 2. Existing architecture (verified)

Frontend:
- Next.js and TypeScript
- PDF upload, chat, source inspection
- Next.js same-origin proxy in Codespaces

Backend:
- FastAPI
- PyMuPDF PDF text extraction
- Text chunking and OpenAI embeddings
- Document-scoped retrieval
- Query rewriting and answer generation

Database:
- Supabase PostgreSQL with pgvector
- documents table
- document_chunks table
- SHA-256 file deduplication
- HNSW vector index and full-text index

Existing API:
- POST /documents/ingest
- POST /ask (requires one document_id)
- GET /health/database

## 3. Target architecture (not yet implemented)

Next.js
  |
  v
FastAPI
  |
  +-- Document Catalog
  |     List authorized indexed documents
  |     Resolve metadata and document identities
  |
  +-- Question Orchestrator
  |     Interpret question and optional scope
  |     Identify comparison intent
  |
  +-- Retrieval Service
  |     Discover relevant documents
  |     Retrieve vector and keyword candidates
  |     Rerank and group evidence by document
  |
  +-- Evidence Validation
  |     Check source coverage
  |     Verify dates, values, and document identity
  |
  +-- Answer Service
        Generate grounded answer
        Calculate supported comparisons
        Return document/page/chunk citations

## 4. Search modes

ALL (default):
Search the user's authorized library.

SINGLE:
Search one selected document.

MULTIPLE:
Search a specified set of documents.

COMPARE:
Discover or select relevant documents, retrieve evidence
from each, and compare supported facts.

The application must not assume a billing month solely
from a filename. Document metadata must be verified.

## 5. Planned API contracts

GET /documents
List completed documents available to the authenticated user.

POST /ask
Accept:
- question
- optional document_ids
- optional conversation history

The server resolves the effective search scope and returns:
- answer
- source documents and page references
- evidence supporting comparisons
- missing-evidence information when applicable

The existing single-document API contract must remain functional
during migration.

These contracts are proposals, not implemented endpoints.

## 6. Security boundaries

Before enabling multi-user access:
- Authenticate every request
- Authorize document list and retrieval operations
- Scope queries to the authenticated user or tenant
- Validate requested document IDs against ownership
- Never expose all database documents globally
- Prevent cross-user retrieval and citation leakage
- Avoid logging private PDF content or credentials

Private Codespaces ports are development access controls,
not application-level document authorization.

### Verified security findings — 2026-11-05

- Row Level Security is enabled on documents and document_chunks.
- Neither table currently has RLS policies.
- FastAPI connects to PostgreSQL using the postgres role.
- The postgres role has BYPASSRLS = true.
- The postgres role owns both tables.
- Neither table currently contains an owner_id or user_id column.
- Application-level document authorization is not implemented.

### Required security changes

1. Establish an authenticated user identity.
2. Associate documents with an owner or tenant.
3. Define ownership rules for existing legacy documents.
4. Enforce authorization for ingestion, listing, retrieval, and answers.
5. Replace the runtime BYPASSRLS connection with an appropriately
   restricted database access strategy.
6. Add RLS policies and verify their behavior using the actual
   application database role.
7. Scope document deduplication to authorized ownership.
8. Add tests proving users cannot access each other's documents.

Do not expose unrestricted library-wide retrieval before
these controls have been implemented and verified.

## 7. Retrieval quality

Evaluate:
- Document selection accuracy
- Recall@K for relevant evidence
- Per-document evidence coverage
- Cross-document comparison accuracy
- Citation correctness
- Missing-document and ambiguous-date behavior
- Retrieval latency and embedding cost

Avoid introducing agents or orchestration frameworks
until simpler approaches are measured and found insufficient.

## 8. Implementation sequence

Phase 1: Document catalog and selection
Phase 2: Authorized library-wide retrieval
Phase 3: Cross-document evidence coverage
Phase 4: Grounded comparisons and evaluation
Phase 5: Mobile UX, accessibility, and hardening

Each phase requires tests before expanding the next.

## 9. Current limitations

- Single-document question answering only
- No persisted document library UI
- No cross-document comparisons
- No verified ownership-based document authorization
- PDF reading order can fragment source text
- Original PDFs are not yet stored for source-page rendering
