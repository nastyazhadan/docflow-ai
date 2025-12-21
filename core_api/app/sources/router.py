from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.app.auth.deps import Principal, get_current_principal
from core_api.app.models.sql.knowledge_space import KnowledgeSpace
from core_api.app.models.sql.source_config import SourceConfig, SourceType
from core_api.app.models.sql.user import UserRole
from core_api.app.rag.vector_store import get_qdrant_client
from core_api.app.sources.schemas import (
    SourceConfigCreateRequest,
    SourceConfigItem,
    SourceConfigListResponse,
    SourceConfigUpdateRequest,
)
from core_api.db.session import get_db

router = APIRouter(prefix="/sources", tags=["sources"])
logger = logging.getLogger(__name__)


def _get_indexed_count(space_id: uuid.UUID) -> int | None:
    """Получает количество проиндексированных документов из Qdrant для space."""
    try:
        client = get_qdrant_client()
        collection_name = f"ks_{space_id.hex}"
        collection_info = client.get_collection(collection_name)
        return collection_info.points_count
    except Exception:
        return None


def _to_source_item(source: SourceConfig, space: KnowledgeSpace) -> SourceConfigItem:
    """Преобразует SourceConfig в SourceConfigItem с информацией о статусе индексации."""
    indexed_count = _get_indexed_count(space.id)
    return SourceConfigItem(
        id=str(source.id),
        space_id=space.space_key,
        type=source.type,
        config=source.config,
        enabled=source.enabled,
        created_at=source.created_at,
        indexed_count=indexed_count,
    )


@router.get("", response_model=SourceConfigListResponse)
async def list_sources(
    space_id: str | None = Query(None, description="Filter by space_id (space_key)"),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> SourceConfigListResponse:
    """Список источников для текущего tenant (опционально фильтр по space_id)."""
    tenant_uuid = uuid.UUID(principal.tenant_id)
    
    query = select(SourceConfig).where(SourceConfig.tenant_id == tenant_uuid)
    
    if space_id:
        # Находим space по space_key
        space = await session.scalar(
            select(KnowledgeSpace).where(
                KnowledgeSpace.tenant_id == tenant_uuid,
                KnowledgeSpace.space_key == space_id,
            )
        )
        if space is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")
        query = query.where(SourceConfig.space_id == space.id)
    
    rows = await session.scalars(query.order_by(SourceConfig.created_at.desc()))
    sources = rows.all()
    
    # Загружаем связанные spaces для получения space_key
    space_ids = {s.space_id for s in sources}
    if space_ids:
        spaces = await session.scalars(
            select(KnowledgeSpace).where(KnowledgeSpace.id.in_(space_ids))
        )
        space_map = {s.id: s for s in spaces.all()}
    else:
        space_map = {}
    
    items = []
    for s in sources:
        space = space_map.get(s.space_id)
        if space:
            items.append(_to_source_item(s, space))
        else:
            # Если space не найден, пропускаем (не должно происходить в нормальной работе)
            logger.warning(f"[SOURCES] Space {s.space_id} not found for source {s.id}")
    return SourceConfigListResponse(items=items)


@router.post("", response_model=SourceConfigItem, status_code=status.HTTP_201_CREATED)
async def create_source(
    payload: SourceConfigCreateRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> SourceConfigItem:
    """Создание нового источника."""
    if principal.role == UserRole.VIEWER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    
    tenant_uuid = uuid.UUID(principal.tenant_id)
    
    # Находим space по space_key
    space = await session.scalar(
        select(KnowledgeSpace).where(
            KnowledgeSpace.tenant_id == tenant_uuid,
            KnowledgeSpace.space_key == payload.space_id,
        )
    )
    if space is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")
    
    source = SourceConfig(
        tenant_id=tenant_uuid,
        space_id=space.id,
        type=payload.type,
        config=payload.config,
        enabled=payload.enabled,
    )
    session.add(source)
    
    try:
        await session.flush()
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create source: {exc}",
        ) from exc
    
    return _to_source_item(source, space)


@router.get("/{source_id}", response_model=SourceConfigItem)
async def get_source(
    source_id: str,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> SourceConfigItem:
    """Получение источника по ID."""
    tenant_uuid = uuid.UUID(principal.tenant_id)
    source_uuid = uuid.UUID(source_id)
    
    source = await session.scalar(
        select(SourceConfig).where(
            SourceConfig.id == source_uuid,
            SourceConfig.tenant_id == tenant_uuid,
        )
    )
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    
    space = await session.scalar(
        select(KnowledgeSpace).where(KnowledgeSpace.id == source.space_id)
    )
    if space is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")
    
    return _to_source_item(source, space)


@router.patch("/{source_id}", response_model=SourceConfigItem)
async def update_source(
    source_id: str,
    payload: SourceConfigUpdateRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> SourceConfigItem:
    """Обновление источника."""
    if principal.role == UserRole.VIEWER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    
    tenant_uuid = uuid.UUID(principal.tenant_id)
    source_uuid = uuid.UUID(source_id)
    
    source = await session.scalar(
        select(SourceConfig).where(
            SourceConfig.id == source_uuid,
            SourceConfig.tenant_id == tenant_uuid,
        )
    )
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    
    if payload.config is not None:
        source.config = payload.config
    if payload.enabled is not None:
        source.enabled = payload.enabled
    
    try:
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update source: {exc}",
        ) from exc
    
    space = await session.scalar(
        select(KnowledgeSpace).where(KnowledgeSpace.id == source.space_id)
    )
    if space is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")
    
    return _to_source_item(source, space)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: str,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Удаление источника."""
    if principal.role == UserRole.VIEWER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    
    tenant_uuid = uuid.UUID(principal.tenant_id)
    source_uuid = uuid.UUID(source_id)
    
    source = await session.scalar(
        select(SourceConfig).where(
            SourceConfig.id == source_uuid,
            SourceConfig.tenant_id == tenant_uuid,
        )
    )
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    
    await session.delete(source)
    await session.commit()

