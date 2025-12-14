from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

# Add service directories to sys.path so we can import service modules
SERVICES_DIR = Path(__file__).resolve().parent.parent
for service_dir in ["cleaner", "indexer", "normalizer", "scraper"]:
    service_path = SERVICES_DIR / service_dir
    if service_path.exists() and str(service_path) not in sys.path:
        sys.path.insert(0, str(service_path))

from cleaner_service.main import cleaner_app  # type: ignore[import-untyped]
from indexer_service import main as indexer_main  # type: ignore[import-untyped]
from normalizer_service.main import normalizer_app  # type: ignore[import-untyped]
from scraper_service.main import scraper_app  # type: ignore[import-untyped]


@pytest.fixture
def scraper_client() -> TestClient:
    """Клиент для scraper-service."""
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
def indexer_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
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

    indexer_app.state.ingest_calls = []

    async def fake_call_core_ingest(client, space_id: str, payload: dict):
        indexer_app.state.ingest_calls.append(
            {
                "space_id": space_id,
                "payload": payload,
            }
        )
        items = payload.get("items") or []
        return len(items)

    monkeypatch.setattr(indexer_main, "_call_core_ingest", fake_call_core_ingest)

    with TestClient(indexer_app) as client:
        yield client

    indexer_app.state.ingest_calls = []
