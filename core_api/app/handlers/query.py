"""
Use case для выполнения RAG-запросов.

Отвечает за бизнес-логику запросов:
- Получение индекса для пространства
- Построение query engine
- Выполнение запроса
- Форматирование источников
"""

from core_api.app.models.dto import IngestRequest, IngestResponse, IngestItem
from core_api.app.rag.vector_store import get_vector_store_index


def query_documents(space_id: str, request: IngestRequest) -> IngestResponse:
    """
    Выполняет RAG-запрос к индексированным документам.
    
    Параметры:
    - space_id: идентификатор пространства знаний
    - request: запрос с текстом вопроса и параметрами поиска
    
    Возвращает:
    - QueryResponse с ответом LLM и списком источников
    """
    # Получаем индекс для пространства
    index = get_vector_store_index(space_id)

    # Создаём query engine с указанным top_k
    query_engine = index.as_query_engine(
        similarity_top_k=request.top_k,
    )

    # Выполняем запрос
    response = query_engine.query(request.query)

    # Форматируем источники
    sources: list[IngestItem] = []
    if hasattr(response, "source_nodes") and response.source_nodes:
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

            # Создаём типизированный SourceItem
            sources.append(IngestItem(**source_data))

    return IngestResponse(
        answer=str(response),
        sources=sources,
    )
