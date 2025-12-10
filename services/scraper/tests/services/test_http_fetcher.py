import httpx
import pytest

from scraper_service.models.dto import SourceType
from scraper_service.services.http_fetcher import fetch_urls


@pytest.mark.anyio
async def test_fetch_urls_empty():
    items = await fetch_urls([], timeout=1.0, max_connections=5)
    assert items == []


@pytest.mark.anyio
async def test_fetch_urls_success_and_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/ok":
            return httpx.Response(200, text="ok")
        return httpx.Response(500, text="fail")

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport, base_url="https://example.com") as client:
        items = await fetch_urls(
            ["https://example.com/ok", "https://example.com/bad"],
            timeout=1.0,
            max_connections=5,
            client=client,
        )

    # Ошибочный URL не должен валить весь список
    assert len(items) == 1
    item = items[0]
    assert item.source == SourceType.HTTP
    assert str(item.url) == "https://example.com/ok"
    assert item.content == "ok"
