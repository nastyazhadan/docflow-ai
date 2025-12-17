from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.app.auth.deps import Principal, get_current_principal
from core_api.app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from core_api.app.auth.security import create_access_token, hash_password, verify_password
from core_api.app.models.sql.tenant import Tenant
from core_api.app.models.sql.user import User
from core_api.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_db)) -> TokenResponse:
    """
    Простая регистрация:
    - создаём Tenant по tenant_slug (если нет)
    - создаём User (email уникален в рамках tenant)
    - возвращаем bearer token
    """
    tenant = await session.scalar(select(Tenant).where(Tenant.slug == payload.tenant_slug))
    if tenant is None:
        tenant = Tenant(slug=payload.tenant_slug, name=payload.tenant_name)
        session.add(tenant)
        await session.flush()

    existing = await session.scalar(
        select(User).where(User.tenant_id == tenant.id, User.email == payload.email)
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    session.add(user)

    try:
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists") from exc

    token = create_access_token(
        {
            "sub": str(user.id),
            "tenant_id": str(tenant.id),
            "tenant_slug": tenant.slug,
            "email": user.email,
        }
    )
    return TokenResponse(
        access_token=token,
        tenant_id=str(tenant.id),
        tenant_slug=tenant.slug,
        user_id=str(user.id),
        email=user.email,
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db)) -> TokenResponse:
    """
    Простая авторизация:
    - ищем Tenant по tenant_slug
    - ищем User по email (в рамках tenant)
    - проверяем пароль
    - возвращаем bearer token
    """
    tenant = await session.scalar(select(Tenant).where(Tenant.slug == payload.tenant_slug))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user = await session.scalar(select(User).where(User.tenant_id == tenant.id, User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(
        {
            "sub": str(user.id),
            "tenant_id": str(tenant.id),
            "tenant_slug": tenant.slug,
            "email": user.email,
        }
    )
    return TokenResponse(
        access_token=token,
        tenant_id=str(tenant.id),
        tenant_slug=tenant.slug,
        user_id=str(user.id),
        email=user.email,
        role=user.role,
    )


@router.get("/me")
async def me(principal: Principal = Depends(get_current_principal)) -> dict:
    return {
        "tenant_id": principal.tenant_id,
        "tenant_slug": principal.tenant_slug,
        "user_id": principal.user_id,
        "email": principal.email,
        "role": principal.role,
    }


