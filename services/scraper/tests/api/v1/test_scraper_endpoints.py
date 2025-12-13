from pathlib import Path

from fastapi.testclient import TestClient

from scraper_service.api.v1.endpoints import get_file_reader
from scraper_service.main import scraper_app
from scraper_service.services.file_reader import FileReader

client = TestClient(scraper_app)


def test_scrape_files_only(tmp_path: Path):
    # Готовим файлы
    (tmp_path / "a.txt").write_text("AAA", encoding="utf-8")
    (tmp_path / "b.txt").write_text("BBB", encoding="utf-8")

    # Переопределяем зависимость, чтобы FileReader смотрел в tmp_path
    def override_file_reader() -> FileReader:
        return FileReader(root_dir=tmp_path)

    scraper_app.dependency_overrides[get_file_reader] = override_file_reader

    resp = client.post(
        "/api/v1/scrape",
        json={"file_glob": "**/*.txt"},
    )

    scraper_app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    items = body["items"]

    assert len(items) == 2
    paths = {i["path"] for i in items}
    assert paths == {"a.txt", "b.txt"}
    for i in items:
        assert i["source"] == "file"
        assert "content" in i


def test_scrape_validation_error():
    # Ни file_glob, ни urls не переданы — должна быть 422 из-за валидации
    resp = client.post("/api/v1/scrape", json={})
    assert resp.status_code == 422
