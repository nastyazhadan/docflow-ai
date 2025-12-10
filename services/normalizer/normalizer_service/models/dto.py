from typing import List, Optional

from pydantic import BaseModel, Field


class NormalizerItemIn(BaseModel):
    """
    Входной элемент normalizer-service — результат cleaner-service.
    """
    source: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    url: Optional[str] = None
    raw_content: str = Field(default="")
    cleaned_content: str = Field(default="")


class Metadata(BaseModel):
    """
    Метаданные для чанка — максимально близко к /ingest контракту.
    """
    source: str
    path: str
    url: Optional[str] = None
    title: str
    created_at: str
    chunk_index: int
    total_chunks: int


class NormalizedDocument(BaseModel):
    """
    Один нормализованный документ (чанк), готовый к индексации.
    """
    external_id: str
    text: str
    metadata: Metadata


class NormalizeRequest(BaseModel):
    """
    Запрос к /normalize.

    Формат:
    {
      "items": [...]
    }
    """
    items: List[NormalizerItemIn]


class NormalizeResponse(BaseModel):
    """
    Ответ от /normalize.

    Формат:
    {
      "items": [...]
    }
    """
    items: List[NormalizedDocument]
