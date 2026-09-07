from uuid import UUID

import pytest

from app.services import database_service


DOCUMENT_ID = UUID("11111111-1111-1111-1111-111111111111")


class FakeCursor:
    def __init__(self, fetch_results, fail_chunks=False):
        self.fetch_results = iter(fetch_results)
        self.fail_chunks = fail_chunks
        self.executed = []
        self.chunk_rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, parameters=None):
        self.executed.append((query, parameters))

    def executemany(self, query, parameters):
        self.chunk_rows = list(parameters)
        if self.fail_chunks:
            raise RuntimeError("chunk insert failed")

    def fetchone(self):
        return next(self.fetch_results)


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0

    def cursor(self):
        return self.fake_cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed += 1


def sample_chunks():
    return [
        {
            "chunk_index": 0,
            "page_number": 1,
            "content": "First chunk",
            "embedding": [0.1] * 1536,
        },
        {
            "chunk_index": 1,
            "page_number": 2,
            "content": "Second chunk",
            "embedding": [0.2] * 1536,
        },
    ]


def test_document_and_chunks_commit_once(monkeypatch):
    cursor = FakeCursor([(DOCUMENT_ID, "guide.pdf")])
    connection = FakeConnection(cursor)
    monkeypatch.setattr(database_service, "get_connection", lambda: connection)

    document, created = database_service.create_document_with_chunks(
        filename="guide.pdf",
        file_hash="abc123",
        chunks=sample_chunks(),
    )

    assert created is True
    assert document == {"id": str(DOCUMENT_ID), "filename": "guide.pdf"}
    assert len(cursor.chunk_rows) == 2
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closed == 1
    assert "ingestion_status = 'completed'" in cursor.executed[-1][0]


def test_concurrent_duplicate_returns_completed_document(monkeypatch):
    cursor = FakeCursor([None, (DOCUMENT_ID, "original.pdf")])
    connection = FakeConnection(cursor)
    monkeypatch.setattr(database_service, "get_connection", lambda: connection)

    document, created = database_service.create_document_with_chunks(
        filename="duplicate.pdf",
        file_hash="abc123",
        chunks=sample_chunks(),
    )

    assert created is False
    assert document == {"id": str(DOCUMENT_ID), "filename": "original.pdf"}
    assert cursor.chunk_rows == []
    assert connection.commits == 1
    assert connection.rollbacks == 0


def test_chunk_failure_rolls_back_without_commit(monkeypatch):
    cursor = FakeCursor(
        [(DOCUMENT_ID, "guide.pdf")],
        fail_chunks=True,
    )
    connection = FakeConnection(cursor)
    monkeypatch.setattr(database_service, "get_connection", lambda: connection)

    with pytest.raises(RuntimeError, match="chunk insert failed"):
        database_service.create_document_with_chunks(
            filename="guide.pdf",
            file_hash="abc123",
            chunks=sample_chunks(),
        )

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closed == 1
