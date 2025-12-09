from fastapi.testclient import TestClient

from normalizer_service.main import normalizer_app

client = TestClient(normalizer_app)


def test_normalize_endpoint_creates_documents() -> None:
    payload = {
        "files": [
            {"path": "a.txt", "content": "hello"},
            {"path": "b.txt", "content": "world"},
        ]
    }

    response = client.post("/normalize", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert len(data["documents"]) == 2
    ids = {d["id"] for d in data["documents"]}
    paths = {d["path"] for d in data["documents"]}

    assert ids == {"a.txt", "b.txt"}
    assert paths == {"a.txt", "b.txt"}
