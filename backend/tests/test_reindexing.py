import pytest

from app.services import database_service
from tests.test_database_service import (
    DOCUMENT_ID,
    FakeCursor,
    FakeConnection,
    sample_chunks,
)


def test_reindex_chunk_failure_rolls_back(monkeypatch):
    cursor = FakeCursor(
        [
            (
                DOCUMENT_ID,
                "abc123",
                "completed",
            )
        ],
        fail_chunks=True,
    )

    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        database_service,
        "get_connection",
        lambda: connection,
    )

    with pytest.raises(
        RuntimeError,
        match="chunk insert failed",
    ):
        database_service.reindex_document_chunks(
            document_id=str(DOCUMENT_ID),
            file_hash="abc123",
            chunks=sample_chunks(),
        )

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closed == 1

    queries = [
        query.upper()
        for query, _ in cursor.executed
    ]

    assert any("FOR UPDATE" in q for q in queries)
    assert any(
        "DELETE FROM DOCUMENT_CHUNKS" in q
        for q in queries
    )

def test_successful_reindex_commits_once(monkeypatch):
    cursor = FakeCursor([
        (
            DOCUMENT_ID,
            "abc123",
            "completed",
        )
    ])

    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        database_service,
        "get_connection",
        lambda: connection,
    )

    result = database_service.reindex_document_chunks(
        document_id=str(DOCUMENT_ID),
        file_hash="abc123",
        chunks=sample_chunks(),
    )

    assert result == 2

    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closed == 1

    queries = [
        query.upper()
        for query, _ in cursor.executed
    ]

    assert any("FOR UPDATE" in q for q in queries)
    assert any("DELETE FROM DOCUMENT_CHUNKS" in q for q in queries)
    assert len(cursor.chunk_rows) == 2

def test_reindex_rejects_hash_mismatch(monkeypatch):
    cursor = FakeCursor([
        (
            DOCUMENT_ID,
            "abc123",
            "completed",
        )
    ])

    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        database_service,
        "get_connection",
        lambda: connection,
    )

    with pytest.raises(ValueError, match="Document hash mismatch"):
        database_service.reindex_document_chunks(
            document_id=str(DOCUMENT_ID),
            file_hash="different456",
            chunks=sample_chunks(),
        )

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closed == 1

    queries = [
        query.upper()
        for query, _ in cursor.executed
    ]

    assert any("FOR UPDATE" in query for query in queries)
    assert not any("DELETE FROM" in query for query in queries)
    assert cursor.chunk_rows == []

@pytest.mark.parametrize("status", ["processing", "failed"])
def test_reindex_rejects_incomplete_document(
    monkeypatch,
    status,
):
    cursor = FakeCursor([
        (
            DOCUMENT_ID,
            "abc123",
            status,
        )
    ])

    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        database_service,
        "get_connection",
        lambda: connection,
    )

    with pytest.raises(
        database_service.IncompleteDocumentError,
        match="Only completed documents can be reindexed",
    ):
        database_service.reindex_document_chunks(
            document_id=str(DOCUMENT_ID),
            file_hash="abc123",
            chunks=sample_chunks(),
        )

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closed == 1

    queries = [
        query.upper()
        for query, _ in cursor.executed
    ]

    assert not any("DELETE FROM" in q for q in queries)
    assert cursor.chunk_rows == []

def test_reindex_rejects_missing_document(monkeypatch):
    cursor = FakeCursor([None])
    connection = FakeConnection(cursor)

    monkeypatch.setattr(
        database_service,
        "get_connection",
        lambda: connection,
    )

    with pytest.raises(ValueError, match="Document not found"):
        database_service.reindex_document_chunks(
            document_id=str(DOCUMENT_ID),
            file_hash="abc123",
            chunks=sample_chunks(),
        )

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closed == 1

    queries = [
        query.upper()
        for query, _ in cursor.executed
    ]

    assert any("FOR UPDATE" in query for query in queries)
    assert not any("DELETE FROM" in query for query in queries)
    assert cursor.chunk_rows == []