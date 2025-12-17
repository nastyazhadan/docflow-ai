from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.app.auth.security import decode_access_token
from core_api.app.models.sql.tenant import Tenant
from core_api.app.models.sql.user import User, UserRole
from core_api.db.session import get_db

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    tenant_slug: str
    user_id: str
    email: str
    role: UserRole


async def get_current_principal(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> Principal:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    tenant_id = payload.get("tenant_id")
    user_id = payload.get("sub")
    email = payload.get("email")
    tenant_slug = payload.get("tenant_slug")
    if not tenant_id or not user_id or not email or not tenant_slug:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        tenant_uuid = uuid.UUID(str(tenant_id))
        user_uuid = uuid.UUID(str(user_id))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    tenant = await session.scalar(select(Tenant).where(Tenant.id == tenant_uuid))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await session.scalar(select(User).where(User.id == user_uuid, User.tenant_id == tenant.id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return Principal(
        tenant_id=str(tenant.id),
        tenant_slug=tenant.slug,
        user_id=str(user.id),
        email=user.email,
        role=user.role,
    )


async def get_optional_principal(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> Principal | None:
    """
    Как get_current_principal, но возвращает None если заголовок Authorization отсутствует.
    Нужен для backward-compatible эндпоинтов (/ingest,/query), которые могут дергаться без auth.
    """
    if creds is None:
        return None
    return await get_current_principal(creds=creds, session=session)


