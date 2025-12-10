from typing import List, Optional

from pydantic import BaseModel, Field


class Metadata(BaseModel):
    """
    Метаданные чанка, максимально совместимые с контрактом /ingest.
    """

    source: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    url: Optional[str] = None
    title: str = Field(..., min_length=1)
    created_at: str = Field(..., min_length=1)
    chunk_index: int = Field(..., ge=0)
    total_chunks: int = Field(..., ge=1)


class NormalizedDocument(BaseModel):
    """
    Документ после normalizer-service (один чанк).
    Используем и на входе /index, и в documents для /ingest.
    """

    external_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    metadata: Metadata


class IndexRequest(BaseModel):
    """
    Запрос к /index/{space_id}.

    Формат:
    {
      "items": [ { external_id, text, metadata } ]
    }
    """

    items: List[NormalizedDocument]


class IndexResponse(BaseModel):
    """
    Ответ от indexer-service: сколько документов успешно передано.
    """

    indexed: int = Field(..., ge=0)
