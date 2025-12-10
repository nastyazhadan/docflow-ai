from typing import Any

from pydantic import BaseModel


class NormalizedDocument(BaseModel):
    id: str
    path: str
    content: str


class IndexRequest(BaseModel):
    space_id: str
    documents: list[NormalizedDocument]


class IngestDocument(BaseModel):
    external_id: str
    text: str
    metadata: dict[str, Any]


class IngestPayload(BaseModel):
    documents: list[IngestDocument]
