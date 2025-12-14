"""
Модели данных для Core API.

Определяют структуру запросов и ответов для endpoints:
- /spaces/{id}/ingest - индексация документов
- /spaces/{id}/query - RAG-запросы
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class PipelineContext(BaseModel):
    space_id: str
    tenant_id: Optional[str] = None
    run_id: Optional[str] = None
    started_at: Optional[datetime] = None


class IngestItem(BaseModel):
    external_id: Optional[str] = None
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    # Новый контракт (Поток B)
    context: Optional[PipelineContext] = None
    items: List[IngestItem] = Field(default_factory=list)

    # Старый контракт (legacy)
    documents: List[IngestItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _coerce_legacy(self) -> "IngestRequest":
        # если items пустой, но пришли documents — считаем это items
        if not self.items and self.documents:
            self.items = self.documents
        return self


class IngestResponse(BaseModel):
    indexed: int
