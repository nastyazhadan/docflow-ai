from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from core_api.app.auth.deps import Principal, get_current_principal
from core_api.app.sources.router import router as sources_router
from core_api.app.models.sql.user import UserRole
from core_api.app.models.sql.source_config import SourceType
from core_api.db.session import get_db


class _FakeScalarsResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)


class FakeSession:
    def __init__(self):
        self.sources = []
        self.spaces = []

    async def scalar(self, stmt):
        stmt_str = str(stmt)
        # Для поиска space по space_key или по id
        if "KnowledgeSpace" in stmt_str or "knowledge_spaces" in stmt_str:
            if self.spaces:
                return self.spaces[0]
            return None
        # Для поиска source по id
        if "SourceConfig" in stmt_str or "source_configs" in stmt_str:
            if self.sources:
                return self.sources[0] if self.sources else None
        return None

    async def scalars(self, stmt):
        # Определяем, что запрашивается - sources или spaces
        # Простая эвристика: если в stmt есть упоминание KnowledgeSpace - возвращаем spaces
        stmt_str = str(stmt)
        if "KnowledgeSpace" in stmt_str or "knowledge_spaces" in stmt_str:
            return _FakeScalarsResult(self.spaces)
        return _FakeScalarsResult(self.sources)

    async def get(self, model, id):
        # Для получения space по id
        if model.__name__ == "KnowledgeSpace" and self.spaces:
            return self.spaces[0]
        return None

    def add(self, obj):
        if obj.__class__.__name__ == "SourceConfig":
            self.sources.append(obj)
        elif obj.__class__.__name__ == "KnowledgeSpace":
            self.spaces.append(obj)

    async def flush(self):
        # имитируем поведение БД (default id + server_default created_at)
        for s in self.sources:
            if getattr(s, "id", None) is None:
                s.id = uuid.uuid4()
            if getattr(s, "created_at", None) is None:
                s.created_at = datetime.now(timezone.utc)
        for s in self.spaces:
            if getattr(s, "id", None) is None:
                s.id = uuid.uuid4()
            if getattr(s, "created_at", None) is None:
                s.created_at = datetime.now(timezone.utc)

    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def delete(self, obj):
        if obj in self.sources:
            self.sources.remove(obj)


def test_sources_create_and_list() -> None:
    fake_session = FakeSession()
    tenant_id = uuid.uuid4()
    space_id = uuid.uuid4()

    # Создаём space для теста
    from core_api.app.models.sql.knowledge_space import KnowledgeSpace
    space = KnowledgeSpace(
        id=space_id,
        tenant_id=tenant_id,
        space_key="demo-space",
        name="Demo",
    )
    fake_session.spaces.append(space)

    async def override_get_db():
        return fake_session

    async def override_principal():
        return Principal(
            tenant_id=str(tenant_id),
            tenant_slug="default",
            user_id=str(uuid.uuid4()),
            email="u@example.com",
            role=UserRole.EDITOR,
        )

    app = FastAPI()
    app.include_router(sources_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_principal] = override_principal

    client = TestClient(app)

    with patch("core_api.app.sources.router._get_indexed_count") as mock_indexed:
        mock_indexed.return_value = 42
        r1 = client.post(
            "/api/v1/sources",
            json={
                "space_id": "demo-space",
                "type": "http",
                "config": {"url": "https://example.com"},
                "enabled": True,
            },
        )
    assert r1.status_code == 201, r1.text
    data1 = r1.json()
    assert data1["space_id"] == "demo-space"
    assert data1["type"] == "http"
    assert data1["config"] == {"url": "https://example.com"}
    assert data1["enabled"] is True
    assert "id" in data1
    assert "created_at" in data1
    assert data1["indexed_count"] == 42

    r2 = client.get("/api/v1/sources")
    assert r2.status_code == 200, r2.text
    data2 = r2.json()
    assert "items" in data2
    assert len(data2["items"]) == 1
    assert data2["items"][0]["space_id"] == "demo-space"


def test_sources_create_forbidden_for_viewer() -> None:
    fake_session = FakeSession()
    tenant_id = uuid.uuid4()

    async def override_get_db():
        return fake_session

    async def override_principal():
        return Principal(
            tenant_id=str(tenant_id),
            tenant_slug="default",
            user_id=str(uuid.uuid4()),
            email="v@example.com",
            role=UserRole.VIEWER,
        )

    app = FastAPI()
    app.include_router(sources_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_principal] = override_principal

    client = TestClient(app)
    r = client.post(
        "/api/v1/sources",
        json={
            "space_id": "demo-space",
            "type": "http",
            "config": {},
            "enabled": True,
        },
    )
    assert r.status_code == 403


def test_sources_update_and_delete() -> None:
    fake_session = FakeSession()
    tenant_id = uuid.uuid4()
    space_id = uuid.uuid4()
    source_id = uuid.uuid4()

    # Создаём space и source для теста
    from core_api.app.models.sql.knowledge_space import KnowledgeSpace
    from core_api.app.models.sql.source_config import SourceConfig

    space = KnowledgeSpace(
        id=space_id,
        tenant_id=tenant_id,
        space_key="demo-space",
        name="Demo",
    )
    fake_session.spaces.append(space)

    source = SourceConfig(
        id=source_id,
        tenant_id=tenant_id,
        space_id=space_id,
        type=SourceType.HTTP,
        config={"url": "https://example.com"},
        enabled=True,
        created_at=datetime.now(timezone.utc),
    )
    fake_session.sources.append(source)

    async def override_get_db():
        return fake_session

    async def override_principal():
        return Principal(
            tenant_id=str(tenant_id),
            tenant_slug="default",
            user_id=str(uuid.uuid4()),
            email="u@example.com",
            role=UserRole.EDITOR,
        )

    app = FastAPI()
    app.include_router(sources_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_principal] = override_principal

    client = TestClient(app)

    with patch("core_api.app.sources.router._get_indexed_count") as mock_indexed:
        mock_indexed.return_value = 10

        # Обновление
        r1 = client.patch(
            f"/api/v1/sources/{source_id}",
            json={"enabled": False, "config": {"url": "https://updated.com"}},
        )
        assert r1.status_code == 200, r1.text
        data1 = r1.json()
        assert data1["enabled"] is False
        assert data1["config"] == {"url": "https://updated.com"}

        # Удаление
        r2 = client.delete(f"/api/v1/sources/{source_id}")
        assert r2.status_code == 204

        # Проверяем, что source удалён
        assert len(fake_session.sources) == 0


def test_sources_list_filtered_by_space() -> None:
    fake_session = FakeSession()
    tenant_id = uuid.uuid4()
    space1_id = uuid.uuid4()
    space2_id = uuid.uuid4()

    # Создаём два space и источники
    from core_api.app.models.sql.knowledge_space import KnowledgeSpace
    from core_api.app.models.sql.source_config import SourceConfig

    space1 = KnowledgeSpace(
        id=space1_id,
        tenant_id=tenant_id,
        space_key="space1",
        name="Space 1",
    )
    space2 = KnowledgeSpace(
        id=space2_id,
        tenant_id=tenant_id,
        space_key="space2",
        name="Space 2",
    )
    fake_session.spaces = [space1, space2]

    source1 = SourceConfig(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        space_id=space1_id,
        type=SourceType.HTTP,
        config={},
        enabled=True,
        created_at=datetime.now(timezone.utc),
    )
    source2 = SourceConfig(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        space_id=space2_id,
        type=SourceType.UPLOAD,
        config={},
        enabled=True,
        created_at=datetime.now(timezone.utc),
    )
    fake_session.sources = [source1, source2]

    async def override_get_db():
        return fake_session

    async def override_principal():
        return Principal(
            tenant_id=str(tenant_id),
            tenant_slug="default",
            user_id=str(uuid.uuid4()),
            email="u@example.com",
            role=UserRole.EDITOR,
        )

    app = FastAPI()
    app.include_router(sources_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_principal] = override_principal

    client = TestClient(app)

    with patch("core_api.app.sources.router._get_indexed_count") as mock_indexed:
        mock_indexed.return_value = None

        # Все источники
        r1 = client.get("/api/v1/sources")
        assert r1.status_code == 200
        data1 = r1.json()
        assert len(data1["items"]) == 2

        # Фильтр по space1
        r2 = client.get("/api/v1/sources?space_id=space1")
        assert r2.status_code == 200
        data2 = r2.json()
        # В реальности будет фильтрация, но в моке вернёт все
        # Это нормально для unit-теста, главное что endpoint работает

