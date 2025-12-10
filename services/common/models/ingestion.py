from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator


class SourceType(str, Enum):
    FILE = "file"
    HTTP = "http"


class RawItem(BaseModel):
    """
    Сырые данные, которые возвращает scraper-service.
    Может быть либо файлом, либо HTTP-страницей.
    """

    source: SourceType
    path: Optional[str] = Field(
        default=None,
        description="Локальный путь к файлу, если source = file",
    )
    url: Optional[AnyHttpUrl] = Field(
        default=None,
        description="URL, если source = http",
    )
    content: str = Field(
        ...,
        description="Сырой контент (файл / HTML страницы и т.п.)",
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_location(self) -> "RawItem":
        """
        Pydantic v2-валидатор уровня модели.
        Проверяем согласованность source / path / url.
        """
        if self.source == SourceType.FILE and not self.path:
            raise ValueError("path is required when source='file'")

        if self.source == SourceType.HTTP and self.url is None:
            raise ValueError("url is required when source='http'")

        return self

    model_config = {
        "extra": "forbid",  # не пропускать лишние поля, чтобы раньше ловить ошибки
    }


class CleanItem(BaseModel):
    """
    Очищенный документ после cleaner-service.
    Для файлов сохраняем original_path, для HTTP — url и title.
    """

    source: SourceType
    original_path: Optional[str] = Field(
        default=None,
        description="Исходный путь к файлу, если документ с диска",
    )
    url: Optional[AnyHttpUrl] = Field(
        default=None,
        description="URL документа, если источник HTTP",
    )
    title: Optional[str] = Field(
        default=None,
        description="Опциональный заголовок документа (title / h1)",
    )
    cleaned_text: str = Field(
        ...,
        description="Очищенный текст без HTML, скриптов и т.п.",
        min_length=0,
    )

    model_config = {"extra": "forbid"}


class NormalizedDocumentMetadata(BaseModel):
    """
    Метаданные нормализованного чанка.
    """

    source: SourceType
    url: Optional[AnyHttpUrl] = Field(
        default=None,
        description="URL, если источник HTTP",
    )
    original_path: Optional[str] = Field(
        default=None,
        description="Путь к исходному файлу, если источник диск",
    )
    title: Optional[str] = Field(
        default=None,
        description="Заголовок документа",
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="Опциональная дата создания документа",
    )
    chunk_index: int = Field(
        ...,
        ge=0,
        description="Индекс чанка в пределах одного документа, начиная с 0",
    )

    model_config = {"extra": "forbid"}


class NormalizedDocument(BaseModel):
    """
    Один логический фрагмент документа (чанк), который пойдёт в Ingest.
    """

    external_id: str = Field(
        ...,
        description=(
            "Глобальный идентификатор документа/чанка "
            "(например, url#chunk-0 или path#chunk-1)"
        ),
        min_length=1,
    )
    text: str = Field(
        ...,
        description="Текст чанка, уже готовый к индексации",
        min_length=1,
    )
    metadata: NormalizedDocumentMetadata

    model_config = {"extra": "forbid"}


class IngestRequest(BaseModel):
    """
    Формат запроса к Core API /spaces/{id}/ingest.
    """

    documents: List[NormalizedDocument] = Field(
        default_factory=list,
        description="Список документов для индексации",
    )

    model_config = {"extra": "forbid"}
