"""
API endpoints для Core API.

Тонкий слой, который только:
- Парсит и валидирует DTO
- Вызывает use cases
- Обрабатывает ошибки и преобразует их в HTTP ответы
"""

import uuid

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.app.auth.deps import Principal, get_optional_principal
from core_api.app.handlers.ingest import ingest_documents as ingest_documents_use_case
from core_api.app.handlers.query import query_documents as query_documents_use_case
from core_api.app.models.dto import IngestRequest, IngestResponse, QueryRequest, QueryResponse
from core_api.app.models.sql.knowledge_space import KnowledgeSpace
from core_api.app.models.sql.user import UserRole
from core_api.db.session import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_db)):
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}


@router.post("/spaces/{space_id}/ingest", response_model=IngestResponse)
async def ingest_documents(
    space_id: str,
    request: IngestRequest,
    principal: Principal | None = Depends(get_optional_principal),
    session: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """
    Индексирует документы в векторное хранилище Qdrant для указанного пространства.

    Этот endpoint вызывается indexer-service после обработки документов через
    пайплайн: scraper → cleaner → normalizer → indexer → core API.

    Параметры:
    - space_id: идентификатор пространства знаний (из URL)
                Каждое пространство имеет свою коллекцию в Qdrant (space_{space_id})
    - request.documents: список нормализованных документов (чанков) для индексации

    Возвращает:
    - indexed: количество успешно проиндексированных документов
    """
    try:
        # Если запрос аутентифицирован — пространство должно существовать в БД для tenant.
        if principal is not None:
            if principal.role == UserRole.VIEWER:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

            tenant_uuid = uuid.UUID(principal.tenant_id)
            ks = await session.scalar(
                select(KnowledgeSpace).where(
                    KnowledgeSpace.tenant_id == tenant_uuid,
                    KnowledgeSpace.space_key == space_id,
                )
            )
            if ks is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")

        return ingest_documents_use_case(space_id, request)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index documents: {exc}",
        ) from exc


@router.post("/spaces/{space_id}/query", response_model=QueryResponse)
async def query(
    space_id: str,
    request: QueryRequest,
    principal: Principal | None = Depends(get_optional_principal),
    session: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """
    Выполняет RAG-запрос к индексированным документам в указанном пространстве.

    RAG (Retrieval-Augmented Generation) процесс:
    1. Векторный поиск: находим top_k наиболее релевантных чанков по запросу
    2. Контекст: передаём найденные чанки в LLM как контекст
    3. Генерация: LLM генерирует ответ на основе контекста

    Параметры:
    - space_id: идентификатор пространства для поиска (из URL)
    - request.query: текст вопроса пользователя
    - request.top_k: количество наиболее релевантных чанков для использования (по умолчанию 5)

    Возвращает:
    - answer: ответ LLM на основе найденных документов
    - sources: список источников (чанков), использованных для генерации ответа
    """
    try:
        # Если запрос аутентифицирован — пространство должно существовать в БД для tenant.
        if principal is not None:
            tenant_uuid = uuid.UUID(principal.tenant_id)
            ks = await session.scalar(
                select(KnowledgeSpace).where(
                    KnowledgeSpace.tenant_id == tenant_uuid,
                    KnowledgeSpace.space_key == space_id,
                )
            )
            if ks is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")

        return query_documents_use_case(space_id, request)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {exc}",
        ) from exc
