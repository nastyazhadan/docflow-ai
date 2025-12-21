from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core_api.app.models.sql.source_config import SourceType


class SourceConfigCreateRequest(BaseModel):
    space_id: str = Field(..., description="Space key (space_id) where source belongs")
    type: SourceType = Field(..., description="Source type: http or upload")
    config: Dict[str, Any] = Field(default_factory=dict, description="Source configuration (JSON)")
    enabled: bool = Field(True, description="Whether source is enabled")


class SourceConfigUpdateRequest(BaseModel):
    config: Optional[Dict[str, Any]] = Field(None, description="Source configuration (JSON)")
    enabled: Optional[bool] = Field(None, description="Whether source is enabled")


class SourceConfigItem(BaseModel):
    id: str
    space_id: str
    type: SourceType
    config: Dict[str, Any]
    enabled: bool
    created_at: datetime
    indexed_count: Optional[int] = Field(None, description="Number of indexed documents (from Qdrant)")


class SourceConfigListResponse(BaseModel):
    items: List[SourceConfigItem]

