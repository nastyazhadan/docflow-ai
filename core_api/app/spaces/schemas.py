from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class SpaceCreateRequest(BaseModel):
    # Это то, что везде в пайплайне называется space_id (demo-space, dominions)
    space_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field("", max_length=256)


class SpaceItem(BaseModel):
    id: str
    space_id: str
    name: str
    created_at: datetime


class SpaceListResponse(BaseModel):
    items: List[SpaceItem]


