from typing import List, Optional

from pydantic import BaseModel, Field


class PipelineContext(BaseModel):
    space_id: str = Field(..., min_length=1)
    tenant_id: Optional[str] = None
    run_id: Optional[str] = None
    started_at: str = Field(..., min_length=1)

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


class IndexRequest(BaseModel):
    context: PipelineContext
    items: List[NormalizedDocument]

    model_config = {"extra": "forbid"}


class IndexResponse(BaseModel):
    context: PipelineContext
    indexed: int = Field(..., ge=0)

    model_config = {"extra": "forbid"}
