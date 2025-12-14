"""
API endpoints для Core API.

Тонкий слой, который только:
- Парсит и валидирует DTO
- Вызывает use cases
- Обрабатывает ошибки и преобразует их в HTTP ответы
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.app.handlers.ingest import ingest_documents as ingest_documents_use_case
from core_api.app.handlers.query import query_documents as query_documents_use_case
from core_api.app.models.dto import (
    IngestRequest,
    IngestResponse,
)
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
async def ingest_documents(space_id: str, request: IngestRequest) -> IngestResponse:
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
        return ingest_documents_use_case(space_id, request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index documents: {exc}",
        ) from exc


@router.post("/spaces/{space_id}/query", response_model=IngestResponse)
async def query(space_id: str, request: IngestRequest) -> IngestResponse:
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
        return query_documents_use_case(space_id, request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {exc}",
        ) from exc
