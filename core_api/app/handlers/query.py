"""
Use case для выполнения RAG-запросов.

Отвечает за бизнес-логику запросов:
- Получение индекса для пространства
- Построение query engine
- Выполнение запроса
- Форматирование источников
"""

import logging

from core_api.app.models.dto import QueryRequest, QueryResponse, SourceItem
from core_api.app.rag.vector_store import get_vector_store_index

logger = logging.getLogger(__name__)


def query_documents(space_id: str, request: QueryRequest) -> QueryResponse:
    """
    Выполняет RAG-запрос к индексированным документам.
    
    Параметры:
    - space_id: идентификатор пространства знаний
    - request: запрос с текстом вопроса и параметрами поиска
    
    Возвращает:
    - QueryResponse с ответом LLM и списком источников
    """
    logger.info(
        "[QUERY] Processing query for space_id=%s query_len=%d top_k=%d",
        space_id,
        len(request.query),
        request.top_k,
    )
    
    # Получаем индекс для пространства
    index = get_vector_store_index(space_id)

    # Создаём query engine с указанным top_k
    query_engine = index.as_query_engine(
        similarity_top_k=request.top_k,
    )

    # Выполняем запрос
    response = query_engine.query(request.query)

    # Форматируем источники
    sources: list[SourceItem] = []
    if hasattr(response, "source_nodes") and response.source_nodes:
        logger.info(
            "[QUERY] Found %d source nodes for space_id=%s",
            len(response.source_nodes),
            space_id,
        )
        for node in response.source_nodes:
            text_preview = (
                node.text[:200] + "..."
                if len(node.text) > 200
                else node.text
            )

            # Создаём словарь для SourceItem
            source_data: dict = {
                "text": text_preview,
                "score": getattr(node, "score", None),
            }

            # Добавляем метаданные, если они есть
            if node.metadata:
                source_data.update(node.metadata)
                # Логируем метаданные для отладки
                logger.debug(
                    "[QUERY] Source node metadata: space_id=%s path=%s external_id=%s",
                    space_id,
                    node.metadata.get("path"),
                    node.metadata.get("external_id"),
                )

            # Создаём типизированный SourceItem
            sources.append(SourceItem(**source_data))
    else:
        logger.warning(
            "[QUERY] No source nodes found for space_id=%s",
            space_id,
        )

    return QueryResponse(
        answer=str(response),
        sources=sources,
    )
