import asyncio
import os

from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers


os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import main  # noqa: E402


def pdf_upload(content=b"%PDF- test bytes"):
    return UploadFile(
        filename="guide.pdf",
        file=__import__("io").BytesIO(content),
        headers=Headers({"content-type": "application/pdf"}),
    )


def test_empty_pdf_returns_useful_400_before_database_or_openai(monkeypatch):
    monkeypatch.setattr(
        main,
        "extract_pdf_text",
        lambda file_bytes: [{"page_number": 1, "text": "   "}],
    )
    monkeypatch.setattr(
        main,
        "get_document_by_hash",
        lambda file_hash: (_ for _ in ()).throw(AssertionError("database called")),
    )
    monkeypatch.setattr(
        main,
        "create_embedding",
        lambda text: (_ for _ in ()).throw(AssertionError("OpenAI called")),
    )

    try:
        asyncio.run(main.ingest_document(pdf_upload()))
    except HTTPException as error:
        assert error.status_code == 400
        assert "no extractable text" in error.detail
    else:
        raise AssertionError("Expected an HTTPException")


def test_existing_upload_preserves_response_shape_and_skips_embeddings(monkeypatch):
    monkeypatch.setattr(
        main,
        "extract_pdf_text",
        lambda file_bytes: [{"page_number": 1, "text": "Useful text"}],
    )
    monkeypatch.setattr(
        main,
        "get_document_by_hash",
        lambda file_hash: {"id": "document-id", "filename": "original.pdf"},
    )
    monkeypatch.setattr(
        main,
        "create_embedding",
        lambda text: (_ for _ in ()).throw(AssertionError("OpenAI called")),
    )

    response = asyncio.run(main.ingest_document(pdf_upload()))

    assert response == {
        "document_id": "document-id",
        "filename": "original.pdf",
        "status": "already_exists",
    }


def test_racing_duplicate_uses_atomic_database_result(monkeypatch):
    monkeypatch.setattr(
        main,
        "extract_pdf_text",
        lambda file_bytes: [{"page_number": 1, "text": "Useful text"}],
    )
    monkeypatch.setattr(main, "get_document_by_hash", lambda file_hash: None)
    monkeypatch.setattr(main, "create_embedding", lambda text: [0.1] * 1536)
    monkeypatch.setattr(
        main,
        "create_document_with_chunks",
        lambda **kwargs: (
            {"id": "document-id", "filename": "original.pdf"},
            False,
        ),
    )

    response = asyncio.run(main.ingest_document(pdf_upload()))

    assert response == {
        "document_id": "document-id",
        "filename": "original.pdf",
        "status": "already_exists",
    }


def test_successful_ingestion_preserves_response_shape(monkeypatch):
    monkeypatch.setattr(
        main,
        "extract_pdf_text",
        lambda file_bytes: [{"page_number": 1, "text": "Useful text"}],
    )
    monkeypatch.setattr(main, "get_document_by_hash", lambda file_hash: None)
    monkeypatch.setattr(main, "create_embedding", lambda text: [0.1] * 1536)
    monkeypatch.setattr(
        main,
        "create_document_with_chunks",
        lambda **kwargs: (
            {"id": "document-id", "filename": "guide.pdf"},
            True,
        ),
    )

    response = asyncio.run(main.ingest_document(pdf_upload()))

    assert response == {
        "document_id": "document-id",
        "filename": "guide.pdf",
        "chunk_count": 1,
        "status": "ingested",
    }
