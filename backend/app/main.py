import hashlib
import logging
import os
import traceback
from uuid import UUID

import psycopg
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from openai import OpenAIError
from pydantic import BaseModel, Field, field_validator

from app.services.embedding_service import create_embedding
from app.services.chunking_service import (
    chunk_pages,
    chunk_text,
)
from app.services.pdf_service import (
    extract_pdf_text,
    has_pdf_signature,
)
from app.services.retrieval_service import rank_chunks
from app.services.database_service import (
    test_database_connection,
    get_document,
    get_document_by_hash,
    create_document_with_chunks,
    search_similar_chunks,
    DatabaseConfigurationError,
    IncompleteDocumentError,
)
from app.services.rag_service import generate_answer
from fastapi.middleware.cors import CORSMiddleware
from app.services.query_rewrite_service import rewrite_query


logger = logging.getLogger("uvicorn.error")


def log_external_failure(service: str, error: Exception):
    """Log a useful traceback without logging exception text or local values."""
    frames = traceback.extract_tb(error.__traceback__)
    sanitized_traceback = "\n".join(
        (
            f'  File "{frame.filename}", line {frame.lineno}, '
            f"in {frame.name}"
        )
        for frame in frames
    )

    if not sanitized_traceback:
        sanitized_traceback = "  <no traceback available>"

    logger.error(
        "%s failure (exception_type=%s)\n"
        "Traceback (most recent call last):\n%s",
        service,
        type(error).__name__,
        sanitized_traceback,
    )


def positive_int_setting(name: str, default: int) -> int:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be a positive integer") from error

    if value <= 0:
        raise RuntimeError(f"{name} must be a positive integer")

    return value


MAX_PDF_UPLOAD_BYTES = positive_int_setting(
    "MAX_PDF_UPLOAD_BYTES",
    10 * 1024 * 1024,
)
MAX_PDF_PAGES = positive_int_setting("MAX_PDF_PAGES", 100)

app = FastAPI(
    title="DocMind RAG API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DatabaseConfigurationError)
@app.exception_handler(psycopg.Error)
async def database_error_handler(request, error):
    log_external_failure("Database", error)

    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "The document service is temporarily unavailable. "
                "Please try again."
            )
        },
    )


@app.exception_handler(OpenAIError)
async def openai_error_handler(request, error):
    log_external_failure("OpenAI", error)

    return JSONResponse(
        status_code=502,
        content={
            "detail": (
                "The AI service is temporarily unavailable. "
                "Please try again."
            )
        },
    )


@app.exception_handler(IncompleteDocumentError)
async def incomplete_document_error_handler(request, error):
    return JSONResponse(
        status_code=409,
        content={
            "detail": (
                "This document is not ready yet. "
                "Please retry the upload."
            )
        },
    )


class ConversationTurn(BaseModel):
    question: str
    answer: str


class AskRequest(BaseModel):
    document_id: UUID
    question: str
    history: list[ConversationTurn] = Field(
        default_factory=list
    )

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question must not be empty")

        return value


async def read_pdf_pages(file: UploadFile):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    file_bytes = await file.read(MAX_PDF_UPLOAD_BYTES + 1)

    if len(file_bytes) > MAX_PDF_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                "The PDF is too large. "
                f"The maximum upload size is {MAX_PDF_UPLOAD_BYTES} bytes."
            ),
        )

    if not has_pdf_signature(file_bytes):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid PDF.",
        )

    try:
        pages = extract_pdf_text(file_bytes)
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail="The PDF could not be read. It may be damaged or invalid.",
        ) from error

    if len(pages) > MAX_PDF_PAGES:
        page_label = "page" if MAX_PDF_PAGES == 1 else "pages"

        raise HTTPException(
            status_code=413,
            detail=(
                "The PDF has too many pages. "
                f"The maximum is {MAX_PDF_PAGES} {page_label}."
            ),
        )

    return file_bytes, pages


def require_completed_document(document_id: UUID):
    document = get_document(document_id)

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    if document["ingestion_status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail="This document is not ready for questions.",
        )

    return document


def validate_question(question: str) -> str:
    if not question.strip():
        raise HTTPException(
            status_code=422,
            detail="Question must not be empty.",
        )

    return question


@app.get("/")
def root():
    return {
        "message": "DocMind RAG API is running"
    }


@app.get("/health/database")
def database_health():
    result = test_database_connection()

    return {
        "database": "connected",
        "result": result,
    }


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
):
    _, pages = await read_pdf_pages(file)
    full_text = "\n".join(page["text"] for page in pages)

    return {
        "filename": file.filename,
        "pages": len(pages),
        "characters": len(full_text),
        "preview": full_text[:500],
    }


@app.post("/documents/chunks")
async def preview_chunks(
    file: UploadFile = File(...),
):
    _, pages = await read_pdf_pages(file)

    chunks = chunk_pages(pages)

    return {
        "filename": file.filename,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


@app.post("/documents/ingest")
async def ingest_document(
    file: UploadFile = File(...),
):
    file_bytes, pages = await read_pdf_pages(file)

    # IMPORTANT:
    # Keep page metadata while creating chunks
    chunks = chunk_pages(pages)

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail=(
                "The PDF contains no extractable text. "
                "Scanned PDFs require OCR before upload."
            ),
        )

    # Generate SHA-256 hash for duplicate detection
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    existing_document = get_document_by_hash(file_hash)

    if existing_document:
        return {
            "document_id": existing_document["id"],
            "filename": existing_document["filename"],
            "status": "already_exists",
        }

    for chunk in chunks:
        chunk["embedding"] = create_embedding(
            chunk["content"]
        )

    document, created = create_document_with_chunks(
        filename=file.filename,
        file_hash=file_hash,
        chunks=chunks,
    )

    if not created:
        return {
            "document_id": document["id"],
            "filename": document["filename"],
            "status": "already_exists",
        }

    return {
        "document_id": document["id"],
        "filename": file.filename,
        "chunk_count": len(chunks),
        "status": "ingested",
    }


@app.post("/embeddings/test")
async def test_embedding(text: str):
    embedding = create_embedding(text)

    return {
        "text": text,
        "dimensions": len(embedding),
        "preview": embedding[:10],
    }


@app.post("/search/test")
async def test_semantic_search(
    file: UploadFile = File(...),
    question: str = "What experience does this person have with forecasting?",
):
    validate_question(question)
    _, pages = await read_pdf_pages(file)

    full_text = "\n".join(
        page["text"]
        for page in pages
    )

    chunks = chunk_text(full_text)

    chunks_with_embeddings = []

    for index, chunk in enumerate(chunks):
        embedding = create_embedding(chunk)

        chunks_with_embeddings.append({
            "chunk_index": index,
            "text": chunk,
            "embedding": embedding,
        })

    query_embedding = create_embedding(question)

    ranked_chunks = rank_chunks(
        query_embedding,
        chunks_with_embeddings,
    )

    return {
        "question": question,
        "total_chunks": len(chunks),
        "top_results": ranked_chunks[:3],
    }


@app.post("/search")
async def search_documents(
    document_id: UUID,
    question: str = Query(...),
):
    validate_question(question)
    require_completed_document(document_id)

    query_embedding = create_embedding(question)

    results = search_similar_chunks(
        query_embedding=query_embedding,
        document_id=str(document_id),
        limit=3,
    )

    return {
        "document_id": str(document_id),
        "question": question,
        "results": results,
    }


@app.post("/ask")
def ask_document(request: AskRequest):
    require_completed_document(request.document_id)

    conversation_history = [
        {
            "question": turn.question,
            "answer": turn.answer,
        }
        for turn in request.history
    ]

    rewritten_query = rewrite_query(
        question=request.question,
        conversation_history=conversation_history,
    )

    question_embedding = create_embedding(
        rewritten_query
    )

    retrieved_chunks = search_similar_chunks(
        query_embedding=question_embedding,
        document_id=str(request.document_id),
        limit=3,
    )

    answer = generate_answer(
        question=request.question,
        retrieved_chunks=retrieved_chunks,
        resolved_question=rewritten_query,
    )

    return {
        "document_id": str(request.document_id),
        "question": request.question,
        "answer": answer,
        "rewritten_query": rewritten_query,
        "sources": [
            {
                "document_id": chunk["document_id"],
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
                "similarity": chunk["similarity"],
                "content": chunk["content"],
            }
            for chunk in retrieved_chunks
        ],
    }
