"""
Core API - основной API сервис для DocFlow.

Отвечает за:
- Индексацию документов в векторное хранилище (Qdrant)
- Выполнение RAG-запросов к проиндексированным документам
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from core_api.app.api.v1.endpoints import router as api_v1_router
from core_api.app.auth.router import router as auth_router
from core_api.app.spaces.router import router as spaces_router
from core_api.app.sources.router import router as sources_router
from core_api.app.config.config import configure_llm_from_env
from core_api.db.session import check_db_connection, dispose_engine, init_engine

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


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

# Auth (только v1, без legacy-экспорта)
app.include_router(auth_router, prefix="/api/v1")

# Spaces management (только v1)
app.include_router(spaces_router, prefix="/api/v1")

# Sources management (только v1)
app.include_router(sources_router, prefix="/api/v1")
