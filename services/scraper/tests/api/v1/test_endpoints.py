import os
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from scraper_service.core import config as config_module
from scraper_service.main import create_app


@pytest.fixture
def temp_root_dir(tmp_path: Path) -> Path:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "a.txt").write_text("hello", encoding="utf-8")
    (root / "b.txt").write_text("world", encoding="utf-8")
    return root


@pytest.fixture
def client(temp_root_dir: Path) -> Generator[TestClient, None, None]:
    # Подменяем переменную окружения, чтобы сервис смотрел в нашу tmp-директорию
    os.environ["SCRAPER_ROOT_DIR"] = str(temp_root_dir)

    # Сбрасываем кэш get_settings, чтобы он перечитал SCRAPER_ROOT_DIR
    config_module.get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_scrape_returns_files(client: TestClient) -> None:
    response = client.get("/api/v1/scrape")
    assert response.status_code == 200

    payload = response.json()
    assert payload["total_files"] == 2

    paths = {f["path"] for f in payload["files"]}
    contents = {f["content"] for f in payload["files"]}

    assert paths == {"a.txt", "b.txt"}
    assert contents == {"hello", "world"}
