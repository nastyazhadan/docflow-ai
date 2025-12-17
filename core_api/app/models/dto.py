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


class QueryRequest(BaseModel):
    """Запрос для RAG-поиска по пространству."""

    query: str = Field(..., description="Текст вопроса пользователя")
    top_k: int = Field(5, ge=1, le=50, description="Количество наиболее релевантных чанков")


class SourceItem(BaseModel):
    """Один источник (документ/чанк), использованный для ответа."""

    text: str = Field(..., description="Превью текста чанка (до 200 символов)")
    score: Optional[float] = Field(None, description="Оценка релевантности чанка к запросу")

    model_config = {
        "extra": "allow",  # позволяем дополнительные произвольные поля метаданных
    }


class QueryResponse(BaseModel):
    """Ответ на RAG-запрос."""

    answer: str = Field(..., description="Ответ LLM на основе найденных документов")
    sources: List[SourceItem] = Field(
        default_factory=list,
        description="Список источников (чанков) с метаданными, использованных для генерации ответа",
    )
