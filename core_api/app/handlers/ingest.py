"""
Use case для индексации документов.

Отвечает за бизнес-логику индексации:
- Валидация входных данных
- Преобразование DTO в LlamaDocument
- Вызов функций индексации
"""

import uuid

from core_api.app.models.dto import IngestRequest, IngestResponse
from core_api.app.rag.mappers import documents_to_llama
from core_api.app.rag.vector_store import add_documents_to_index


def ingest_documents(knowledge_space_id: uuid.UUID, request: IngestRequest) -> IngestResponse:
    """
    Индексирует документы в векторное хранилище для указанного пространства.
    
    Параметры:
    - knowledge_space_id: UUID пространства знаний (KnowledgeSpace.id)
    - request: запрос с документами для индексации
    
    Возвращает:
    - IngestResponse с количеством проиндексированных документов
    """
    # Обработка пустого запроса
    if not request.items:
        return IngestResponse(indexed=0)

    # Преобразуем DTO в LlamaDocument
    llama_documents = documents_to_llama(request.items)

    # Добавляем документы в индекс
    indexed = add_documents_to_index(knowledge_space_id, llama_documents)

    return IngestResponse(indexed=indexed)
