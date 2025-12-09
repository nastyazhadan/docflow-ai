from pydantic import BaseModel


class Document(BaseModel):
    id: str
    path: str
    content: str


class IndexRequest(BaseModel):
    space_id: str
    documents: list[Document]


class IngestRequest(BaseModel):
    documents: list[Document]
