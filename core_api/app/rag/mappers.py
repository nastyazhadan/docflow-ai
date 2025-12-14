"""
Мапперы для преобразования DTO в объекты LlamaIndex.

Отвечает за преобразование документов из формата API (DTO)
в формат, используемый LlamaIndex для индексации.
"""

from llama_index.core import Document as LlamaDocument

from core_api.app.models.dto import PipelineContext


def document_to_llama(doc: PipelineContext) -> LlamaDocument:
    """
    Преобразует Document DTO в LlamaDocument для индексации.
    
    Параметры:
    - doc: Document DTO из API запроса
    
    Возвращает:
    - LlamaDocument для добавления в векторный индекс
    """
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

    return LlamaDocument(
        text=doc.text,
        metadata=metadata,
        id_=doc.external_id,
    )


def documents_to_llama(documents: list[PipelineContext]) -> list[LlamaDocument]:
    """
    Преобразует список Document DTO в список LlamaDocument.
    
    Параметры:
    - documents: список Document DTO из API запроса
    
    Возвращает:
    - список LlamaDocument для индексации
    """
    return [document_to_llama(doc) for doc in documents]
