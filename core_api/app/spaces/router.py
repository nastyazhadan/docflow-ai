from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.app.auth.deps import Principal, get_current_principal
from core_api.app.models.sql.user import UserRole
from core_api.app.models.sql.knowledge_space import KnowledgeSpace
from core_api.app.rag.vector_store import get_or_create_collection
from core_api.app.spaces.schemas import SpaceCreateRequest, SpaceItem, SpaceListResponse
from core_api.db.session import get_db

router = APIRouter(prefix="/spaces", tags=["spaces"])
logger = logging.getLogger(__name__)


def _to_space_item(space: KnowledgeSpace) -> SpaceItem:
    return SpaceItem(
        id=str(space.id),
        space_id=space.space_key,
        name=space.name,
        created_at=space.created_at,
    )


@router.get("", response_model=SpaceListResponse)
async def list_spaces(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> SpaceListResponse:
    rows = await session.scalars(
        select(KnowledgeSpace)
        .where(KnowledgeSpace.tenant_id == uuid.UUID(principal.tenant_id))
        .order_by(KnowledgeSpace.created_at.desc())
    )
    items = [_to_space_item(s) for s in rows.all()]
    return SpaceListResponse(items=items)


@router.post("", response_model=SpaceItem, status_code=status.HTTP_201_CREATED)
async def create_space(
    payload: SpaceCreateRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> SpaceItem:
    if principal.role == UserRole.VIEWER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # проверка существования (дружелюбнее, чем ловить IntegrityError)
    existing = await session.scalar(
        select(KnowledgeSpace).where(
            KnowledgeSpace.tenant_id == uuid.UUID(principal.tenant_id),
            KnowledgeSpace.space_key == payload.space_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Space already exists")

    space = KnowledgeSpace(
        tenant_id=uuid.UUID(principal.tenant_id),
        space_key=payload.space_id,
        name=payload.name or "",
    )
    session.add(space)

    try:
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Space already exists") from exc

    # Привязка к Qdrant: создаём (или проверяем) коллекцию для knowledge_space_id сразу при создании space.
    # Это гарантирует, что KnowledgeSpace соответствует индексу в Qdrant.
    try:
        get_or_create_collection(space.id)
    except Exception as exc:
        logger.exception("[SPACES] Failed to create/check Qdrant collection for knowledge_space_id=%s", space.id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Qdrant is unavailable") from exc

    return _to_space_item(space)


