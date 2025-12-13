from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator, field_validator


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


class ItemBase(BaseModel):
    source: str = Field(..., min_length=1)
    path: Optional[str] = Field(default=None)
    url: Optional[str] = None

    @model_validator(mode="after")
    def validate_location(self) -> "ItemBase":
        s = (self.source or "").lower()
        if s == "file" and not self.path:
            raise ValueError("path is required when source='file'")
        if s == "http" and not self.url:
            raise ValueError("url is required when source='http'")
        return self

    model_config = {"extra": "forbid"}


class CleanItemIn(ItemBase):
    content: str = Field(default="")


class CleanItemOut(ItemBase):
    raw_content: str
    cleaned_content: str


class CleanRequest(BaseModel):
    context: PipelineContext
    items: List[CleanItemIn]

    model_config = {"extra": "forbid"}


class CleanResponse(BaseModel):
    context: PipelineContext
    items: List[CleanItemOut]

    model_config = {"extra": "forbid"}
