import base64

from fastapi.testclient import TestClient

from scraper_service.main import scraper_app

client = TestClient(scraper_app)


def _b64(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


def test_scrape_files_only():
    resp = client.post(
        "/api/v1/scrape",
        json={
            "context": {"space_id": "space-1"},
            "files": [
                {"name": "a.txt", "content_b64": _b64("AAA"), "encoding": "base64"},
                {"name": "b.txt", "content_b64": _b64("BBB"), "encoding": "base64"},
            ],
        },
    )

    assert resp.status_code == 200
    body = resp.json()

    assert body["context"]["space_id"] == "space-1"

    items = body["items"]
    assert len(items) == 2

    paths = {i["path"] for i in items}
    assert paths == {"a.txt", "b.txt"}

    for i in items:
        assert i["source"] == "file"
        assert "content" in i
        assert i.get("url") is None


def test_scrape_validation_error():
    # Ни urls, ни files не переданы — должна быть 422 из-за валидации
    resp = client.post("/api/v1/scrape", json={"context": {"space_id": "space-1"}})
    assert resp.status_code == 422


def test_space_id_strips_and_rejects_blank():
    # space_id из пробелов должен дать 422 (даже если files есть)
    resp = client.post(
        "/api/v1/scrape",
        json={
            "context": {"space_id": "   "},
            "files": [{"name": "a.txt", "content_b64": _b64("AAA"), "encoding": "base64"}],
        },
    )
    assert resp.status_code == 422
