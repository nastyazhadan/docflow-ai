from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core_api.app.api.v1.endpoints import router as legacy_router
from core_api.app.auth.deps import Principal, get_optional_principal
from core_api.app.models.sql.user import UserRole
from core_api.db.session import get_db


class FakeSession:
    async def scalar(self, _stmt):
        # we won't reach DB validation in these tests (we test role check first)
        return None

    async def execute(self, _stmt):
        return None


def test_viewer_forbidden_on_ingest_when_authenticated() -> None:
    app = FastAPI()
    app.include_router(legacy_router, prefix="/api/v1")

    async def override_principal():
        return Principal(
            tenant_id=str(uuid.uuid4()),
            tenant_slug="default",
            user_id=str(uuid.uuid4()),
            email="v@example.com",
            role=UserRole.VIEWER,
        )

    async def override_db():
        return FakeSession()

    app.dependency_overrides[get_optional_principal] = override_principal
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    r = client.post("/api/v1/spaces/demo-space/ingest", json={"items": [{"text": "hi", "metadata": {}}]})
    assert r.status_code == 403


def test_viewer_allowed_on_query_when_authenticated() -> None:
    app = FastAPI()
    app.include_router(legacy_router, prefix="/api/v1")

    async def override_principal():
        return Principal(
            tenant_id=str(uuid.uuid4()),
            tenant_slug="default",
            user_id=str(uuid.uuid4()),
            email="v@example.com",
            role=UserRole.VIEWER,
        )

    async def override_db():
        return FakeSession()

    app.dependency_overrides[get_optional_principal] = override_principal
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    # query handler will fail later (no mocked index), but we only want to ensure it doesn't 403 on role check
    r = client.post("/api/v1/spaces/demo-space/query", json={"query": "hi", "top_k": 3})
    assert r.status_code != 403


