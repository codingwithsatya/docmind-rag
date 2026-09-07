from uuid import UUID
import os

import psycopg
from dotenv import load_dotenv


load_dotenv()


def test_database_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is not configured")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")

            result = cursor.fetchone()

    return result[0]


def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is not configured")

    return psycopg.connect(database_url)


def test_database_connection():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()

    return result[0]


def build_keyword_query(question: str) -> str:
    stop_words = {
        "what",
        "when",
        "where",
        "why",
        "how",
        "which",
        "who",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "do",
        "does",
        "did",
        "should",
        "could",
        "would",
        "can",
        "a",
        "an",
        "the",
        "of",
        "to",
        "for",
        "in",
        "on",
        "at",
        "after",
        "before",
        "instead",
    }

    words = (
        question.lower()
        .replace("?", "")
        .replace(",", "")
        .split()
    )

    keywords = [
        word
        for word in words
        if word not in stop_words
    ]

    return " OR ".join(keywords)


def create_document(
    filename: str,
    file_hash: str,
) -> UUID:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO documents (
                    filename,
                    file_hash
                )
                VALUES (%s, %s)
                RETURNING id;
                """,
                (
                    filename,
                    file_hash,
                ),
            )

            document_id = cursor.fetchone()[0]

        connection.commit()

    return document_id


def create_document_chunk(
    document_id: UUID,
    chunk_index: int,
    page_number: int,
    content: str,
    embedding: list[float],
):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO document_chunks (
                    document_id,
                    chunk_index,
                    page_number,
                    content,
                    embedding
                )
                VALUES (%s, %s, %s, %s, %s);
                """,
                (
                    document_id,
                    chunk_index,
                    page_number,
                    content,
                    embedding,
                ),
            )

        connection.commit()


def search_similar_chunks(
    query_embedding: list[float],
    document_id: str,
    limit: int = 3,
):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    document_id,
                    chunk_index,
                    page_number,
                    content,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM document_chunks
                WHERE document_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (
                    query_embedding,
                    document_id,
                    query_embedding,
                    limit,
                ),
            )

            rows = cursor.fetchall()

    return [
        {
            "id": str(row[0]),
            "document_id": str(row[1]),
            "chunk_index": row[2],
            "page_number": row[3],
            "content": row[4],
            "similarity": float(row[5]),
        }
        for row in rows
    ]


def get_document_by_hash(file_hash: str):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, filename
                FROM documents
                WHERE file_hash = %s
                LIMIT 1;
                """,
                (file_hash,),
            )

            row = cursor.fetchone()

    if not row:
        return None

    return {
        "id": str(row[0]),
        "filename": row[1],
    }


def search_chunks_by_keyword(
    query: str,
    document_id: str,
    limit: int = 5,
):
    keyword_query = build_keyword_query(query)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    document_id,
                    chunk_index,
                    page_number,
                    content,
                    ts_rank_cd(
                        to_tsvector('english', content),
                        websearch_to_tsquery('english', %s)
                    ) AS rank
                FROM document_chunks
                WHERE
                    document_id = %s
                    AND to_tsvector('english', content)
                        @@ websearch_to_tsquery('english', %s)
                ORDER BY rank DESC
                LIMIT %s;
                """,
                (
                    keyword_query,
                    document_id,
                    keyword_query,
                    limit,
                ),
            )

            rows = cursor.fetchall()

    return [
        {
            "id": str(row[0]),
            "document_id": str(row[1]),
            "chunk_index": row[2],
            "page_number": row[3],
            "content": row[4],
            "keyword_rank": float(row[5]),
        }
        for row in rows
    ]
