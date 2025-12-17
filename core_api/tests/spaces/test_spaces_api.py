from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

from core_api.app.auth.deps import Principal, get_current_principal
from core_api.app.spaces.router import router as spaces_router
from core_api.app.models.sql.user import UserRole
from core_api.db.session import get_db


class _FakeScalarsResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)


class FakeSession:
    def __init__(self):
        self.spaces = []

    async def scalar(self, _stmt):
        # Для юнит-теста нам достаточно "нет существующего space"
        return None

    async def scalars(self, _stmt):
        return _FakeScalarsResult(self.spaces)

    def add(self, obj):
        self.spaces.append(obj)

    async def flush(self):
        # имитируем поведение БД (default id + server_default created_at)
        for s in self.spaces:
            if getattr(s, "id", None) is None:
                s.id = uuid.uuid4()
            if getattr(s, "created_at", None) is None:
                s.created_at = datetime.now(timezone.utc)

    async def commit(self):
        return None

    async def rollback(self):
        return None


def test_spaces_create_and_list() -> None:
    fake_session = FakeSession()

    async def override_get_db():
        return fake_session

    async def override_principal():
        return Principal(
            tenant_id=str(uuid.uuid4()),
            tenant_slug="default",
            user_id=str(uuid.uuid4()),
            email="u@example.com",
            role=UserRole.EDITOR,
        )

    app = FastAPI()
    app.include_router(spaces_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_principal] = override_principal

    client = TestClient(app)

    with patch("core_api.app.spaces.router.get_or_create_collection") as mock_get_or_create:
        mock_get_or_create.return_value = "space_demo-space"
        r1 = client.post("/api/v1/spaces", json={"space_id": "demo-space", "name": "Demo"})
    assert r1.status_code == 201, r1.text
    data1 = r1.json()
    assert data1["space_id"] == "demo-space"
    assert data1["name"] == "Demo"
    assert "id" in data1
    assert "created_at" in data1

    r2 = client.get("/api/v1/spaces")
    assert r2.status_code == 200, r2.text
    data2 = r2.json()
    assert "items" in data2
    assert len(data2["items"]) == 1
    assert data2["items"][0]["space_id"] == "demo-space"


def test_spaces_create_forbidden_for_viewer() -> None:
    fake_session = FakeSession()

    async def override_get_db():
        return fake_session

    async def override_principal():
        return Principal(
            tenant_id=str(uuid.uuid4()),
            tenant_slug="default",
            user_id=str(uuid.uuid4()),
            email="v@example.com",
            role=UserRole.VIEWER,
        )

    app = FastAPI()
    app.include_router(spaces_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_principal] = override_principal

    client = TestClient(app)
    r = client.post("/api/v1/spaces", json={"space_id": "demo-space", "name": "Demo"})
    assert r.status_code == 403


