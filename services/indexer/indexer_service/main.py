from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, HTTPException, Request, status

from indexer_service.models.dto import IndexRequest, IndexResponse
from indexer_service.services.indexer import build_ingest_payload

API_HOST = os.getenv("API_HOST", "api")
API_PORT = int(os.getenv("API_PORT", "8000"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    base_url = f"http://{API_HOST}:{API_PORT}"
    client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
    app.state.http_client = client
    try:
        yield
    finally:
        await client.aclose()


indexer_app = FastAPI(title="Indexer Service", version="0.1.0", lifespan=lifespan)


async def _call_core_ingest(
        client: httpx.AsyncClient,
        space_id: str,
        payload: dict,
) -> int:
    response = await client.post(f"/spaces/{space_id}/ingest", json=payload)

    try:
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise exc

    data = response.json()
    if isinstance(data, dict) and isinstance(data.get("indexed"), int):
        return data["indexed"]

    # fallback: считаем по items
    items = payload.get("items") or []
    return len(items)


@indexer_app.post("/index/{space_id}", response_model=IndexResponse)
async def index_endpoint(space_id: str, request: IndexRequest, raw_request: Request) -> IndexResponse:
    # приоритет у context
    effective_space_id = request.context.space_id or space_id

    if not request.items:
        return IndexResponse(context=request.context, indexed=0)

    payload = build_ingest_payload(context=request.context, items=request.items)

    client: httpx.AsyncClient = raw_request.app.state.http_client

    try:
        indexed = await _call_core_ingest(client, effective_space_id, payload)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Core API ingest error: {exc}",
        ) from exc

    return IndexResponse(context=request.context, indexed=indexed)
