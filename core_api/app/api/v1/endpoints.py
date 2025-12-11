from fastapi import APIRouter, HTTPException, status
from llama_index.core import Document as LlamaDocument

from core_api.app.models.dto import (
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
)
from core_api.app.rag.vector_store import add_documents_to_index, get_vector_store_index

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Используется для проверки работоспособности сервиса
    (например, в Docker healthchecks или мониторинге).
    """
    return {"status": "ok"}


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
    # Обработка пустого запроса
    if not request.documents:
        return IngestResponse(indexed=0)

    # Преобразуем документы из формата API в формат LlamaIndex
    llama_documents: list[LlamaDocument] = []
    for doc in request.documents:
        metadata = {
            "external_id": doc.external_id,
            "source": doc.metadata.source,
            "path": doc.metadata.path,
            "url": doc.metadata.url,
            "title": doc.metadata.title,
            "created_at": doc.metadata.created_at,
            "chunk_index": doc.metadata.chunk_index,
            "total_chunks": doc.metadata.total_chunks,
        }

        llama_doc = LlamaDocument(
            text=doc.text,
            metadata=metadata,
            id_=doc.external_id,
        )
        llama_documents.append(llama_doc)

    try:
        indexed = add_documents_to_index(space_id, llama_documents)
        return IngestResponse(indexed=indexed)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index documents: {exc}",
        ) from exc


@router.post("/spaces/{space_id}/query", response_model=QueryResponse)
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
        index = get_vector_store_index(space_id)

        query_engine = index.as_query_engine(
            similarity_top_k=request.top_k,
        )

        response = query_engine.query(request.query)

        sources: list[dict] = []
        if hasattr(response, "source_nodes") and response.source_nodes:
            for node in response.source_nodes:
                text_preview = (
                    node.text[:200] + "..."
                    if len(node.text) > 200
                    else node.text
                )

                source_info: dict = {
                    "text": text_preview,
                    "score": getattr(node, "score", None),
                }

                if node.metadata:
                    source_info.update(node.metadata)

                sources.append(source_info)

        return QueryResponse(
            answer=str(response),
            sources=sources,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {exc}",
        ) from exc
