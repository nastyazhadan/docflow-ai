from __future__ import annotations

from fastapi import APIRouter, Depends

from scraper_service.core.config import get_settings
from scraper_service.models.dto import (
    FileContent,
    RawItem,
    ScrapeRequest,
    ScrapeResponse,
    SourceType,
)
from scraper_service.services.file_reader import FileReader
from scraper_service.services.http_fetcher import fetch_urls

router = APIRouter()


def get_file_reader() -> FileReader:
    settings = get_settings()
    # Можно ограничить расширения, если нужно, пока читаем всё
    return FileReader(root_dir=settings.scraper_root_dir)


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest, reader: FileReader = Depends(get_file_reader)) -> ScrapeResponse:
    settings = get_settings()
    items: list[RawItem] = []

    if request.file_glob:
        files: list[FileContent] = reader.read_all(pattern=request.file_glob)
        for f in files:
            if not f.content.strip():
                continue
            items.append(RawItem(source=SourceType.FILE, path=f.path, content=f.content))

    if request.urls:
        http_items = await fetch_urls(
            [str(u) for u in request.urls],
            timeout=settings.http_timeout,
            max_connections=settings.http_max_connections,
        )
        items.extend(http_items)

    return ScrapeResponse(context=request.context, items=items)
