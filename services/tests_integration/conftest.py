from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from cleaner_service.main import cleaner_app
from indexer_service import main as indexer_main
from indexer_service.services.indexer import build_ingest_payload
from normalizer_service.main import normalizer_app
from scraper_service.core.config import get_settings
from scraper_service.main import scraper_app


@pytest.fixture
def scraper_root_dir(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """
    Подменяем SCRAPER_ROOT_DIR на временную директорию для теста.
    Так мы не трогаем реальные data/docs и делаем тесты детерминированными.
    """
    monkeypatch.setenv("SCRAPER_ROOT_DIR", str(tmp_path))

    # Сбрасываем lru_cache для get_settings, чтобы перечитались ENV
    get_settings.cache_clear()  # type: ignore[attr-defined]

    return tmp_path


@pytest.fixture
def scraper_client(scraper_root_dir: Path) -> TestClient:  # noqa: ARG001
    """
    Клиент для scraper-service.

    Важно: scraper_root_dir вызывается первым и успевает
    подменить SCRAPER_ROOT_DIR до первого get_settings().
    """
    return TestClient(scraper_app)


@pytest.fixture
def cleaner_client() -> TestClient:
    """Клиент для cleaner-service."""
    return TestClient(cleaner_app)


@pytest.fixture
def normalizer_client() -> TestClient:
    """Клиент для normalizer-service."""
    return TestClient(normalizer_app)


@pytest.fixture
def indexer_client(
        monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """
    Клиент для indexer-service с подменой вызова Core API.

    Вместо реального HTTP-запроса к Core:
    - используем build_ingest_payload для формирования body
    - складываем вызовы в indexer_app.state.ingest_calls
    - возвращаем len(documents) как indexed

    ВАЖНО: TestClient запускаем как контекст-менеджер,
    чтобы сработал lifespan и создался app.state.http_client.
    """
    indexer_app = indexer_main.indexer_app

    # Список вызовов к /spaces/{id}/ingest, который будем проверять в тестах
    indexer_app.state.ingest_calls = []

    async def fake_call_core_ingest(client, space_id: str, documents):
        # client нам не нужен, но оставляем в сигнатуре
        payload = build_ingest_payload(documents)
        indexer_app.state.ingest_calls.append(
            {
                "space_id": space_id,
                "payload": payload,
            }
        )
        # Эмулируем, что Core проиндексировал все документы
        return len(payload["documents"])

    # Подменяем приватный вызов на нашу заглушку
    monkeypatch.setattr(indexer_main, "_call_core_ingest", fake_call_core_ingest)

    # Критично: запускаем через "with", чтобы lifespan отработал
    with TestClient(indexer_app) as client:
        yield client

    # Чистим состояние после тестов
    indexer_app.state.ingest_calls = []
