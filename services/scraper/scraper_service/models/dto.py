from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator, field_validator


class PipelineContext(BaseModel):
    space_id: str = Field(..., min_length=1, max_length=128)
    tenant_id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    run_id: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("space_id")
    @classmethod
    def strip_space_id(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("space_id must be non-empty")
        return v

    model_config = {"extra": "forbid"}


class FileContent(BaseModel):
    path: str
    content: str


class SourceType(str, Enum):
    FILE = "file"
    HTTP = "http"


class RawItem(BaseModel):
    source: SourceType
    path: Optional[str] = Field(default=None)
    url: Optional[AnyHttpUrl] = Field(default=None)
    content: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_location(self) -> "RawItem":
        if self.source == SourceType.FILE and not self.path:
            raise ValueError("path is required when source='file'")
        if self.source == SourceType.HTTP and self.url is None:
            raise ValueError("url is required when source='http'")
        return self

    model_config = {"extra": "forbid"}


class ScrapeRequest(BaseModel):
    context: PipelineContext

    file_glob: Optional[str] = Field(default=None)
    urls: Optional[List[AnyHttpUrl]] = Field(default=None)

    @model_validator(mode="after")
    def validate_non_empty(self) -> "ScrapeRequest":
        if not self.file_glob and not self.urls:
            raise ValueError("At least one of file_glob or urls must be provided")
        return self

    model_config = {"extra": "forbid"}


class ScrapeResponse(BaseModel):
    context: PipelineContext
    items: List[RawItem]

    model_config = {"extra": "forbid"}
