import importlib

from fastapi.testclient import TestClient


def make_client(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("KB_DB_PATH", str(db))
    import app.main as main
    main = importlib.reload(main)
    main.init_db()
    return TestClient(main.app)


def test_create_and_get_document(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    response = client.post(
        "/v1/documents",
        json={"title": "Docker deployment", "content": "Deploy FastAPI with Docker", "tags": ["devops"]},
    )
    assert response.status_code == 201
    document_id = response.json()["id"]
    assert client.get(f"/v1/documents/{document_id}").json()["title"] == "Docker deployment"


def test_search_returns_relevant_document(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    client.post("/v1/documents", json={"title": "Thread pools", "content": "Tune Java thread pools for concurrency", "tags": ["java"]})
    client.post("/v1/documents", json={"title": "SQL indexes", "content": "Indexes improve database lookup performance", "tags": ["database"]})
    response = client.get("/v1/search", params={"q": "thread concurrency"})
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Thread pools"
    assert "<mark>" in response.json()[0]["snippet"]


def test_search_supports_tag_filter(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    client.post("/v1/documents", json={"title": "Java API", "content": "Build a REST API", "tags": ["backend"]})
    client.post("/v1/documents", json={"title": "Python API", "content": "Build a REST API", "tags": ["python"]})
    response = client.get("/v1/search", params={"q": "API", "tag": "python"})
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Python API"


def test_missing_document_is_404(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    assert client.get("/v1/documents/999").status_code == 404
