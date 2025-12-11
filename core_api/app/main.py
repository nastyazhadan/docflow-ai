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
from core_api.app.core.config import configure_llm_from_env


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifecycle-менеджер FastAPI.

    Выполняется при старте приложения:
    - Настраивает LLM и embeddings на основе переменных окружения
    - Используется для инициализации глобальных настроек LlamaIndex
    """
    configure_llm_from_env()
    yield


# Создаём FastAPI приложение
app = FastAPI(
    title="DocFlow Core API",
    version="0.1.0",
    lifespan=lifespan,
)

# Подключаем роутеры (v1 API)
app.include_router(api_v1_router)
