import os
from uuid import UUID

import psycopg
from fastapi.testclient import TestClient
from openai import OpenAIError


os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import main  # noqa: E402


DOCUMENT_ID = "11111111-1111-1111-1111-111111111111"
client = TestClient(main.app, raise_server_exceptions=False)


def completed_document():
    return {
        "id": DOCUMENT_ID,
        "filename": "guide.pdf",
        "ingestion_status": "completed",
    }


def test_empty_question_is_rejected_without_service_calls(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_document",
        lambda document_id: (_ for _ in ()).throw(AssertionError("database called")),
    )

    response = client.post(
        "/ask",
        json={"document_id": DOCUMENT_ID, "question": "   ", "history": []},
    )

    assert response.status_code == 422
    assert "Question must not be empty" in response.text


def test_invalid_document_uuid_is_rejected_without_database_call(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_document",
        lambda document_id: (_ for _ in ()).throw(AssertionError("database called")),
    )

    response = client.post(
        "/ask",
        json={"document_id": "not-a-uuid", "question": "What is this?"},
    )

    assert response.status_code == 422


def test_missing_document_returns_404_before_openai(monkeypatch):
    monkeypatch.setattr(main, "get_document", lambda document_id: None)
    monkeypatch.setattr(
        main,
        "create_embedding",
        lambda text: (_ for _ in ()).throw(AssertionError("OpenAI called")),
    )

    response = client.post(
        "/ask",
        json={"document_id": DOCUMENT_ID, "question": "What is this?"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found."}


def test_incomplete_document_returns_409_before_openai(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_document",
        lambda document_id: {
            **completed_document(),
            "ingestion_status": "processing",
        },
    )
    monkeypatch.setattr(
        main,
        "create_embedding",
        lambda text: (_ for _ in ()).throw(AssertionError("OpenAI called")),
    )

    response = client.post(
        "/ask",
        json={"document_id": DOCUMENT_ID, "question": "What is this?"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "This document is not ready for questions."
    }


def test_non_pdf_content_is_rejected_even_with_pdf_mime_type():
    response = client.post(
        "/documents/ingest",
        files={"file": ("fake.pdf", b"plain text", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "The uploaded file is not a valid PDF."}


def test_damaged_pdf_returns_safe_error():
    response = client.post(
        "/documents/ingest",
        files={"file": ("broken.pdf", b"%PDF-broken", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "The PDF could not be read. It may be damaged or invalid."
    }


def test_empty_pdf_returns_400(monkeypatch):
    monkeypatch.setattr(
        main,
        "extract_pdf_text",
        lambda file_bytes: [{"page_number": 1, "text": "  "}],
    )

    response = client.post(
        "/documents/ingest",
        files={"file": ("empty.pdf", b"%PDF-empty", "application/pdf")},
    )

    assert response.status_code == 400
    assert "no extractable text" in response.json()["detail"]


def test_oversized_upload_returns_413_before_pdf_parsing(monkeypatch):
    monkeypatch.setattr(main, "MAX_PDF_UPLOAD_BYTES", 8)
    monkeypatch.setattr(
        main,
        "extract_pdf_text",
        lambda file_bytes: (_ for _ in ()).throw(AssertionError("PDF parsed")),
    )

    response = client.post(
        "/documents/ingest",
        files={"file": ("large.pdf", b"%PDF-1234", "application/pdf")},
    )

    assert response.status_code == 413
    assert "maximum upload size is 8 bytes" in response.json()["detail"]


def test_page_limit_returns_413(monkeypatch):
    monkeypatch.setattr(main, "MAX_PDF_PAGES", 1)
    monkeypatch.setattr(
        main,
        "extract_pdf_text",
        lambda file_bytes: [
            {"page_number": 1, "text": "Page one"},
            {"page_number": 2, "text": "Page two"},
        ],
    )

    response = client.post(
        "/documents/ingest",
        files={"file": ("long.pdf", b"%PDF-long", "application/pdf")},
    )

    assert response.status_code == 413
    assert "maximum is 1 page" in response.json()["detail"]


def test_database_error_does_not_expose_details(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_document",
        lambda document_id: (_ for _ in ()).throw(
            psycopg.OperationalError("password=do-not-expose")
        ),
    )

    response = client.post(
        "/ask",
        json={"document_id": DOCUMENT_ID, "question": "What is this?"},
    )

    assert response.status_code == 503
    assert "do-not-expose" not in response.text
    assert response.json() == {
        "detail": (
            "The document service is temporarily unavailable. Please try again."
        )
    }


def test_openai_error_does_not_expose_details(monkeypatch):
    monkeypatch.setattr(main, "get_document", lambda document_id: completed_document())
    monkeypatch.setattr(
        main,
        "create_embedding",
        lambda text: (_ for _ in ()).throw(OpenAIError("key=do-not-expose")),
    )

    response = client.post(
        "/ask",
        json={"document_id": DOCUMENT_ID, "question": "What is this?"},
    )

    assert response.status_code == 502
    assert "do-not-expose" not in response.text
    assert response.json() == {
        "detail": "The AI service is temporarily unavailable. Please try again."
    }


def test_successful_ask_preserves_response_shape_and_uses_uuid(monkeypatch):
    observed = []
    monkeypatch.setattr(
        main,
        "get_document",
        lambda document_id: observed.append(document_id) or completed_document(),
    )
    monkeypatch.setattr(main, "create_embedding", lambda text: [0.1] * 1536)
    monkeypatch.setattr(main, "search_similar_chunks", lambda **kwargs: [])
    monkeypatch.setattr(main, "generate_answer", lambda **kwargs: "Answer")

    response = client.post(
        "/ask",
        json={"document_id": DOCUMENT_ID, "question": "What is this?"},
    )

    assert response.status_code == 200
    assert observed == [UUID(DOCUMENT_ID)]
    assert response.json() == {
        "document_id": DOCUMENT_ID,
        "question": "What is this?",
        "answer": "Answer",
        "rewritten_query": "What is this?",
        "sources": [],
    }
