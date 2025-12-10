from typing import List, Optional

from pydantic import BaseModel, model_validator, Field


class NormalizerItemIn(BaseModel):
    """
    Входной элемент normalizer-service — результат cleaner-service.

    Для файлов:
    - source = "file"
    - path обязателен
    - url может быть None

    Для HTTP:
    - source = "http"
    - url обязательна
    - path может быть None
    """

    source: str = Field(..., min_length=1)
    path: Optional[str] = Field(default=None)
    url: Optional[str] = None
    raw_content: str = Field(default="")
    cleaned_content: str = Field(default="")

    @model_validator(mode="after")
    def validate_location(self) -> "NormalizerItemIn":
        s = (self.source or "").lower()

        if s == "file" and not self.path:
            raise ValueError("path is required when source='file'")

        if s == "http" and not self.url:
            raise ValueError("url is required when source='http'")

        return self


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
