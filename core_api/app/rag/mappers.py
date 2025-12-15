"""
Мапперы для преобразования DTO в объекты LlamaIndex.

Отвечает за преобразование документов из формата API (DTO)
в формат, используемый LlamaIndex для индексации.
"""

from typing import Any, Dict, Mapping, Union

from llama_index.core import Document as LlamaDocument

from core_api.app.models.dto import IngestItem


DocLike = Union[IngestItem, Mapping[str, Any]]


def _to_plain_dict(doc: DocLike) -> Dict[str, Any]:
    """
    Приводит IngestItem или dict к обычному словарю.
    """
    if isinstance(doc, Mapping):
        return dict(doc)

    # Pydantic v2
    if hasattr(doc, "model_dump"):
        return doc.model_dump()  # type: ignore[no-any-return]

    # Pydantic v1
    if hasattr(doc, "dict"):
        return doc.dict()  # type: ignore[no-any-return]

    # Fallback: собираем вручную через getattr
    return {
        "external_id": getattr(doc, "external_id", None),
        "text": getattr(doc, "text", ""),
        "metadata": getattr(doc, "metadata", {}) or {},
    }


def document_to_llama(doc: DocLike) -> LlamaDocument:
    """
    Преобразует один документ (IngestItem или dict) в LlamaDocument.

    Поддерживает оба варианта:
    - doc: IngestItem (Pydantic-модель)
    - doc: dict c ключами text / metadata и т.п.
    """
    data = _to_plain_dict(doc)

    raw_meta: Any = data.get("metadata") or {}

    # Приводим metadata к dict, независимо от того, что туда пришло
    if isinstance(raw_meta, Mapping):
        meta_dict: Dict[str, Any] = dict(raw_meta)
    elif hasattr(raw_meta, "model_dump"):
        meta_dict = raw_meta.model_dump()  # type: ignore[assignment]
    elif hasattr(raw_meta, "dict"):
        meta_dict = raw_meta.dict()  # type: ignore[assignment]
    else:
        meta_dict = {}

    metadata: Dict[str, Any] = {
        "external_id": data.get("external_id"),
        "source": meta_dict.get("source"),
        "path": meta_dict.get("path"),
        "url": meta_dict.get("url"),
        "title": meta_dict.get("title"),
        "created_at": meta_dict.get("created_at"),
        "chunk_index": meta_dict.get("chunk_index"),
        "total_chunks": meta_dict.get("total_chunks"),
    }

    text = data.get("text", "")
    external_id = data.get("external_id")

    return LlamaDocument(
        text=text,
        metadata=metadata,
        id_=external_id,
    )


def documents_to_llama(documents: list[DocLike]) -> list[LlamaDocument]:
    """
    Преобразует список документов (IngestItem или dict) в список LlamaDocument.
    """
    return [document_to_llama(doc) for doc in documents]
