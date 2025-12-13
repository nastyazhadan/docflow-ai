from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class PipelineContext(BaseModel):
    space_id: str = Field(..., min_length=1)
    tenant_id: Optional[str] = None
    run_id: Optional[str] = None
    started_at: str = Field(..., min_length=1)

    model_config = {"extra": "forbid"}


class NormalizerItemIn(BaseModel):
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

    model_config = {"extra": "forbid"}


class Metadata(BaseModel):
    source: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    url: Optional[str] = None
    title: str = Field(..., min_length=1)
    created_at: str = Field(..., min_length=1)
    chunk_index: int = Field(..., ge=0)
    total_chunks: int = Field(..., ge=1)

    model_config = {"extra": "forbid"}


class NormalizedDocument(BaseModel):
    external_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    metadata: Metadata

    model_config = {"extra": "forbid"}


class NormalizeRequest(BaseModel):
    context: PipelineContext
    items: List[NormalizerItemIn]

    model_config = {"extra": "forbid"}


class NormalizeResponse(BaseModel):
    context: PipelineContext
    items: List[NormalizedDocument]

    model_config = {"extra": "forbid"}
