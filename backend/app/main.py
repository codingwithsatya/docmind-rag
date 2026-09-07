import hashlib

from fastapi import FastAPI, UploadFile, File, HTTPException

from app.services.embedding_service import create_embedding
from app.services.chunking_service import (
    chunk_pages,
    chunk_text,
)
from app.services.pdf_service import (
    extract_pdf_info,
    extract_pdf_text,
)
from app.services.retrieval_service import rank_chunks
from app.services.database_service import (
    test_database_connection,
    create_document,
    get_document_by_hash,
    create_document_chunk,
    search_similar_chunks,
)
from app.services.rag_service import generate_answer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from app.services.query_rewrite_service import rewrite_query

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


class ConversationTurn(BaseModel):
    question: str
    answer: str


class AskRequest(BaseModel):
    document_id: str
    question: str
    history: list[ConversationTurn] = Field(
        default_factory=list
    )


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
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported",
        )

    file_bytes = await file.read()

    pdf_info = extract_pdf_info(
        file_bytes=file_bytes,
        filename=file.filename,
    )

    return pdf_info


@app.post("/documents/chunks")
async def preview_chunks(
    file: UploadFile = File(...),
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported",
        )

    file_bytes = await file.read()

    pages = extract_pdf_text(file_bytes)

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
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported",
        )

    file_bytes = await file.read()

    # Generate SHA-256 hash for duplicate detection
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    existing_document = get_document_by_hash(file_hash)

    if existing_document:
        return {
            "document_id": existing_document["id"],
            "filename": existing_document["filename"],
            "status": "already_exists",
        }

    # Extract text page-by-page
    pages = extract_pdf_text(file_bytes)

    # IMPORTANT:
    # Keep page metadata while creating chunks
    chunks = chunk_pages(pages)

    document_id = create_document(
        filename=file.filename,
        file_hash=file_hash,
    )

    for chunk in chunks:
        embedding = create_embedding(
            chunk["content"]
        )

        create_document_chunk(
            document_id=document_id,
            chunk_index=chunk["chunk_index"],
            page_number=chunk["page_number"],
            content=chunk["content"],
            embedding=embedding,
        )

    return {
        "document_id": str(document_id),
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
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported",
        )

    file_bytes = await file.read()

    pages = extract_pdf_text(file_bytes)

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
    document_id: str,
    question: str,
):
    query_embedding = create_embedding(question)

    results = search_similar_chunks(
        query_embedding=query_embedding,
        document_id=document_id,
        limit=3,
    )

    return {
        "document_id": document_id,
        "question": question,
        "results": results,
    }


@app.post("/ask")
def ask_document(request: AskRequest):
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
        document_id=request.document_id,
        limit=3,
    )

    answer = generate_answer(
        question=request.question,
        retrieved_chunks=retrieved_chunks,
        resolved_question=rewritten_query,
    )

    return {
        "document_id": request.document_id,
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
