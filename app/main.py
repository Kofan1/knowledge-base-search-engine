"""Technical knowledge-base search API using SQLite FTS5."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


DB_PATH = os.getenv("KB_DB_PATH", "knowledge.db")


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=100_000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    source: str | None = Field(default=None, max_length=500)


class Document(DocumentCreate):
    id: int
    created_at: str


class SearchResult(Document):
    rank: float
    snippet: str


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '',
                source TEXT,
                created_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                title, content, tags, content='documents', content_rowid='id'
            )"""
        )
        conn.execute(
            """CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
                INSERT INTO documents_fts(rowid, title, content, tags)
                VALUES (new.id, new.title, new.content, new.tags);
            END"""
        )
        conn.execute(
            """CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, title, content, tags)
                VALUES ('delete', old.id, old.title, old.content, old.tags);
            END"""
        )
        conn.execute(
            """CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, title, content, tags)
                VALUES ('delete', old.id, old.title, old.content, old.tags);
                INSERT INTO documents_fts(rowid, title, content, tags)
                VALUES (new.id, new.title, new.content, new.tags);
            END"""
        )


def row_to_document(row: sqlite3.Row) -> dict:
    item = dict(row)
    item["tags"] = [tag for tag in item["tags"].split(",") if tag]
    return item


app = FastAPI(title="Knowledge Base Search Engine", version="1.0.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/documents", response_model=Document, status_code=201)
def create_document(document: DocumentCreate) -> dict:
    created_at = datetime.now(timezone.utc).isoformat()
    tags = ",".join(sorted({tag.strip().lower() for tag in document.tags if tag.strip()}))
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO documents(title, content, tags, source, created_at) VALUES (?, ?, ?, ?, ?)",
            (document.title, document.content, tags, document.source, created_at),
        )
        row = conn.execute("SELECT * FROM documents WHERE id=?", (cursor.lastrowid,)).fetchone()
    return row_to_document(row)


@app.get("/v1/documents/{document_id}", response_model=Document)
def get_document(document_id: int) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return row_to_document(row)


@app.get("/v1/search", response_model=list[SearchResult])
def search_documents(
    q: str = Query(min_length=1, max_length=200),
    tag: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[dict]:
    # FTS5 MATCH provides tokenized search and BM25 ranking. The tag filter
    # is applied after ranking so the query remains easy to understand.
    normalized_query = " ".join(part for part in q.split() if part.isalnum() or "-" in part)
    if not normalized_query:
        raise HTTPException(status_code=400, detail="Search query must contain searchable terms")
    with connect() as conn:
        rows = conn.execute(
            """SELECT d.*, bm25(documents_fts) AS rank,
                      snippet(documents_fts, 1, '<mark>', '</mark>', '...', 24) AS snippet
               FROM documents_fts
               JOIN documents d ON d.id = documents_fts.rowid
               WHERE documents_fts MATCH ?
                 AND (? IS NULL OR ',' || d.tags || ',' LIKE '%,' || lower(?) || ',%')
               ORDER BY rank
               LIMIT ?""",
            (normalized_query, tag, tag.lower() if tag else None, limit),
        ).fetchall()
    results = []
    for row in rows:
        item = row_to_document(row)
        item["rank"] = float(item["rank"])
        results.append(item)
    return results


@app.delete("/v1/documents/{document_id}")
def delete_document(document_id: int) -> dict[str, int]:
    with connect() as conn:
        result = conn.execute("DELETE FROM documents WHERE id=?", (document_id,))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": document_id}

