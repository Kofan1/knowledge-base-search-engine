# Knowledge Base Search Engine

A lightweight technical knowledge-base API built with FastAPI and SQLite FTS5. Users can store engineering documents and search them with ranked full-text results, snippets, and tag filtering.

## Features

- Document ingestion through a REST API
- SQLite FTS5 full-text indexing
- BM25 relevance ranking
- Highlighted search snippets
- Tag filtering
- Persistent local storage
- Docker support and GitHub Actions CI

## Architecture

```text
Client -> FastAPI -> SQLite documents table
                  -> SQLite FTS5 index -> ranked search results
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8001
```

Open the interactive API documentation at http://127.0.0.1:8001/docs.

## Run with Docker

```bash
docker compose up --build
```

## Example requests

Create a document:

```bash
curl -X POST http://127.0.0.1:8001/v1/documents \\
  -H 'Content-Type: application/json' \\
  -d '{
    "title": "Debugging Thread Pools",
    "content": "Use metrics and logs to identify thread pool saturation.",
    "tags": ["java", "backend"]
  }'
```

Search documents:

```bash
curl 'http://127.0.0.1:8001/v1/search?q=thread%20pool&tag=java'
```

## Test

```bash
pytest -q
```

## Resume description

> Built a FastAPI knowledge-base search service using SQLite FTS5 and BM25 ranking; implemented document ingestion, highlighted snippets, tag filtering, Docker deployment, and API tests.

