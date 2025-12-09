from fastapi.testclient import TestClient

from indexer_service.main import app

client = TestClient(app)


def test_index_endpoint_returns_count() -> None:
    payload = {
        "space_id": "test-space",
        "documents": [
            {"id": "a.txt", "path": "a.txt", "content": "hello"},
            {"id": "b.txt", "path": "b.txt", "content": "world"},
        ],
    }

    response = client.post("/index", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["indexed"] == 2
