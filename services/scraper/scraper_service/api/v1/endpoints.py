from __future__ import annotations

from fastapi import APIRouter, HTTPException

from scraper_service.config.config import get_settings
from scraper_service.models.dto import (
    FileContent,
    RawItem,
    ScrapeRequest,
    ScrapeResponse,
    SourceType,
)
from scraper_service.services.http_fetcher import fetch_urls
from scraper_service.services.uploaded_file_decoder import UploadedFileDecoder

router = APIRouter()


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest) -> ScrapeResponse:
    settings = get_settings()
    items: list[RawItem] = []

    if request.files:
        decoder = UploadedFileDecoder()
        try:
            files: list[FileContent] = decoder.decode_to_file_contents(request.files)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        for f in files:
            content = (f.content or "").strip()
            if not content:
                continue
            items.append(RawItem(source=SourceType.FILE, path=f.path, content=content))

    if request.urls:
        http_items = await fetch_urls(
            [str(u) for u in request.urls],
            timeout=settings.http_timeout,
            max_connections=settings.http_max_connections,
        )
        items.extend(http_items)

    return ScrapeResponse(context=request.context, items=items)
