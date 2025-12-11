"""
Core API - основной API сервис для DocFlow.

Отвечает за:
- Индексацию документов в векторное хранилище (Qdrant)
- Выполнение RAG-запросов к проиндексированным документам
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, status

from api.llm_factory import configure_llm_from_env
from api.models import IngestRequest, IngestResponse, QueryRequest, QueryResponse
from api.vector_store import add_documents_to_index, get_vector_store_index
from llama_index.core import Document as LlamaDocument


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
    lifespan=lifespan,  # Подключаем lifecycle-менеджер
)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Используется для проверки работоспособности сервиса
    (например, в Docker healthchecks или мониторинге).
    """
    return {"status": "ok"}


@app.post("/spaces/{space_id}/ingest", response_model=IngestResponse)
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
    # Обработка пустого запроса
    if not request.documents:
        return IngestResponse(indexed=0)

    # Преобразуем документы из формата API в формат LlamaIndex
    # LlamaIndex использует свой класс Document с метаданными
    llama_documents = []
    for doc in request.documents:
        # Собираем метаданные для LlamaIndex
        # Эти метаданные будут сохранены вместе с эмбеддингами в Qdrant
        # и использованы при поиске для отображения источников
        metadata = {
            "external_id": doc.external_id,  # Уникальный ID чанка
            "source": doc.metadata.source,    # Источник: "file" или "http"
            "path": doc.metadata.path,        # Путь к файлу или URL
            "url": doc.metadata.url,          # URL (если источник HTTP)
            "title": doc.metadata.title,      # Заголовок документа
            "created_at": doc.metadata.created_at,  # Время создания
            "chunk_index": doc.metadata.chunk_index,  # Индекс чанка в документе
            "total_chunks": doc.metadata.total_chunks,  # Всего чанков в документе
        }

        # Создаём документ LlamaIndex с текстом и метаданными
        llama_doc = LlamaDocument(
            text=doc.text,           # Текст чанка для индексации
            metadata=metadata,        # Метаданные для поиска и отображения
            id_=doc.external_id,     # Уникальный ID для дедупликации
        )
        llama_documents.append(llama_doc)

    try:
        # Добавляем документы в векторное хранилище
        # Функция автоматически создаст коллекцию, если её нет
        indexed = add_documents_to_index(space_id, llama_documents)
        return IngestResponse(indexed=indexed)
    except Exception as exc:
        # Обработка ошибок индексации (проблемы с Qdrant, эмбеддингами и т.д.)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index documents: {exc}",
        ) from exc


@app.post("/spaces/{space_id}/query", response_model=QueryResponse)
async def query(space_id: str, request: QueryRequest) -> QueryResponse:
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
        # Получаем векторный индекс для указанного пространства
        # Если коллекция не существует, будет создана пустая
        index = get_vector_store_index(space_id)

        # Создаём query engine - это объект LlamaIndex, который:
        # - Выполняет векторный поиск по запросу
        # - Извлекает top_k наиболее релевантных чанков
        # - Формирует промпт с контекстом
        # - Вызывает LLM для генерации ответа
        query_engine = index.as_query_engine(similarity_top_k=request.top_k)

        # Выполняем RAG-запрос
        # LlamaIndex автоматически:
        # 1. Создаёт эмбеддинг запроса
        # 2. Ищет похожие документы в Qdrant
        # 3. Формирует промпт с контекстом
        # 4. Вызывает LLM (настроенный в llm_factory)
        response = query_engine.query(request.query)

        # Извлекаем источники (чанки), использованные для генерации ответа
        # Это нужно для отображения пользователю, откуда взят ответ
        sources = []
        if hasattr(response, "source_nodes") and response.source_nodes:
            for node in response.source_nodes:
                # Собираем информацию об источнике
                source_info = {
                    "text": node.text[:200] + "..." if len(node.text) > 200 else node.text,  # Превью текста
                    "score": getattr(node, "score", None),  # Оценка релевантности (если есть)
                }
                # Добавляем метаданные (source, path, url, title и т.д.)
                # для отображения пользователю, откуда взят ответ
                if node.metadata:
                    source_info.update(node.metadata)
                sources.append(source_info)

        return QueryResponse(
            answer=str(response),  # Ответ LLM
            sources=sources,       # Список источников с метаданными
        )
    except Exception as exc:
        # Обработка ошибок (проблемы с Qdrant, LLM, эмбеддингами и т.д.)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {exc}",
        ) from exc
