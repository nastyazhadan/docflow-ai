from fastapi.testclient import TestClient

from cleaner_service.main import cleaner_app

client = TestClient(cleaner_app)


def test_clean_endpoint_echoes_files() -> None:
    payload = {
        "files": [
            {"path": "a.txt", "content": "hello"},
            {"path": "b.txt", "content": "world"},
        ]
    }

    response = client.post("/clean", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert len(data["files"]) == 2
    assert data["files"][0]["path"] == "a.txt"
    assert data["files"][0]["content"] == "hello"
