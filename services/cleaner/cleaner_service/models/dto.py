from pydantic import BaseModel


class FilePayload(BaseModel):
    path: str
    content: str


class CleanRequest(BaseModel):
    files: list[FilePayload]


class CleanResponse(BaseModel):
    files: list[FilePayload]
