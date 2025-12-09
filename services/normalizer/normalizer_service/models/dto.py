from pydantic import BaseModel


class FilePayload(BaseModel):
    path: str
    content: str


class Document(BaseModel):
    id: str
    path: str
    content: str


class NormalizeRequest(BaseModel):
    files: list[FilePayload]


class NormalizeResponse(BaseModel):
    documents: list[Document]
