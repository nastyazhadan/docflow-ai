from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, List

import httpx
from fastapi import FastAPI, HTTPException, Request, status

from indexer_service.models.dto import IndexRequest, IndexResponse, NormalizedDocument
from indexer_service.services.indexer import build_ingest_payload

API_HOST = os.getenv("API_HOST", "api")
API_PORT = int(os.getenv("API_PORT", "8000"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan-хендлер FastAPI:
    - на старте создаёт httpx.AsyncClient
    - на завершении аккуратно его закрывает

    Никаких глобальных переменных, всё лежит в app.state.
    """
    base_url = f"http://{API_HOST}:{API_PORT}"
    client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
    app.state.http_client = client
    try:
        yield
    finally:
        await client.aclose()


indexer_app = FastAPI(
    title="Indexer Service",
    version="0.1.0",
    lifespan=lifespan,
)


async def _call_core_ingest(
        client: httpx.AsyncClient,
        space_id: str,
        documents: List[NormalizedDocument],
) -> int:
    """
    Делает HTTP-запрос к Core API /spaces/{id}/ingest.
    Возвращает число успешно проиндексированных документов.
    """
    payload = build_ingest_payload(documents)

    response = await client.post(
        f"/spaces/{space_id}/ingest",
        json=payload,
    )

    try:
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise exc

    data = response.json()

    # Если Core API возвращает { "indexed": <int> } — используем это значение.
    if isinstance(data, dict) and isinstance(data.get("indexed"), int):
        return data["indexed"]

    # Иначе — считаем, что успешно отправили всё, что передали.
    return len(documents)


@indexer_app.post("/index/{space_id}", response_model=IndexResponse)
async def index_endpoint(
        space_id: str,
        request: IndexRequest,
        raw_request: Request,
) -> IndexResponse:
    """
    Принимает документы от normalizer-service и прокидывает их в Core API.

    - вход:  { "items": [NormalizedDocument] }
    - в Core: { "documents": [NormalizedDocument] }
    - выход:  { "indexed": <количество> }
    """
    documents = list(request.items)

    # Пограничный случай: нечего индексировать
    if not documents:
        return IndexResponse(indexed=0)

    client: httpx.AsyncClient = raw_request.app.state.http_client

    try:
        indexed = await _call_core_ingest(client, space_id, documents)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Core API ingest error: {exc}",
        ) from exc

    return IndexResponse(indexed=indexed)
