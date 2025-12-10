from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator


class FileContent(BaseModel):
    """Внутреннее представление файла, которое возвращает FileReader."""
    path: str
    content: str


class SourceType(str, Enum):
    FILE = "file"
    HTTP = "http"


class RawItem(BaseModel):
    """
    Унифицированный формат сырых данных для ingestion-пайплайна.

    Это по сути тот же контракт, что мы заложили в common-модели:
    - source: "file" или "http"
    - path: путь к файлу (для файлов)
    - url: URL (для HTTP)
    - content: сырой текст/HTML
    """

    source: SourceType
    path: Optional[str] = Field(
        default=None,
        description="Относительный путь к файлу, если source = file",
    )
    url: Optional[AnyHttpUrl] = Field(
        default=None,
        description="URL, если source = http",
    )
    content: str = Field(
        ...,
        description="Содержимое файла или HTML-страницы",
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_location(self) -> "RawItem":
        if self.source == SourceType.FILE and not self.path:
            raise ValueError("path is required when source='file'")
        if self.source == SourceType.HTTP and self.url is None:
            raise ValueError("url is required when source='http'")
        return self

    model_config = {"extra": "forbid"}


class ScrapeRequest(BaseModel):
    """
    Запрос к /scrape.

    Можно передать:
    - file_glob: glob-паттерн для файлов (относительно root_dir),
    - urls: список URL для HTTP-скачивания.
    Нужно указать хотя бы одно из полей.
    """

    file_glob: Optional[str] = Field(
        default=None,
        description="Glob-паттерн относительно корневой директории",
    )
    urls: Optional[List[AnyHttpUrl]] = Field(
        default=None,
        description="Список URL для HTTP-загрузки",
    )

    @model_validator(mode="after")
    def validate_non_empty(self) -> "ScrapeRequest":
        if not self.file_glob and not self.urls:
            raise ValueError("At least one of file_glob or urls must be provided")
        return self

    model_config = {"extra": "forbid"}


class ScrapeResponse(BaseModel):
    """
    Ответ /scrape — унифицированный список RawItem.
    """

    items: List[RawItem]

    model_config = {"extra": "forbid"}
