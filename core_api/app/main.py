"""
Core API - основной API сервис для DocFlow.

Отвечает за:
- Индексацию документов в векторное хранилище (Qdrant)
- Выполнение RAG-запросов к проиндексированным документам
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from core_api.app.api.v1.endpoints import router as api_v1_router
from core_api.app.config.config import configure_llm_from_env
from core_api.db.session import check_db_connection, dispose_engine, init_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_llm_from_env()

    # DB init + fail-fast check
    init_engine()
    await check_db_connection()

    try:
        yield
    finally:
        await dispose_engine()


# Создаём FastAPI приложение
app = FastAPI(
    title="DocFlow Core API",
    version="0.1.0",
    lifespan=lifespan,
)

# Подключаем роутеры (v1 API)
# было:
# app.include_router(api_v1_router)

# стало:
app.include_router(api_v1_router, prefix="/api/v1")
app.include_router(api_v1_router, include_in_schema=False)  # backward-compatible без дублей в Swagger
