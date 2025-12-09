from pydantic import BaseModel


class FileContent(BaseModel):
    path: str
    content: str


class ScrapeResponse(BaseModel):
    files: list[FileContent]
    total_files: int
