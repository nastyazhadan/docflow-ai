from __future__ import annotations

import asyncio
import logging
from typing import List, Optional, Sequence

import httpx

from scraper_service.models.dto import RawItem, SourceType

logger = logging.getLogger(__name__)


async def fetch_urls(
        urls: Sequence[str],
        timeout: float,
        max_connections: int,
        client: Optional[httpx.AsyncClient] = None,
) -> List[RawItem]:
    """Параллельно подтягивает HTTP-страницы и возвращает RawItem.

    - concurrency ограничен max_connections через asyncio.Semaphore
    - ошибки по отдельным URL не валят весь запрос — они логируются и пропускаются
    """
    if not urls:
        return []

    semaphore = asyncio.Semaphore(max_connections)

    async def _fetch_one(url: str, http_client: httpx.AsyncClient) -> Optional[RawItem]:
        try:
            async with semaphore:
                resp = await http_client.get(url, timeout=timeout)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to fetch %s: %s", url, exc)
            return None

        return RawItem(
            source=SourceType.HTTP,
            url=url,
            content=resp.text,
        )

    async def _run_with_client(http_client: httpx.AsyncClient) -> List[RawItem]:
        tasks = [asyncio.create_task(_fetch_one(u, http_client)) for u in urls]
        results = await asyncio.gather(*tasks)
        return [item for item in results if item is not None]

    if client is not None:
        return await _run_with_client(client)

    async with httpx.AsyncClient() as new_client:
        return await _run_with_client(new_client)
