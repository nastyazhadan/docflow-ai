import logging
from typing import Any

from fastapi import FastAPI, Path

from indexer_service.models.dto import IndexRequest, IngestRequest
from indexer_service.services.indexer import Indexer

logging.basicConfig(level=logging.INFO)

indexer_app = FastAPI(
    title="Indexer Service",
    version="0.1.0",
)

_indexer = Indexer()


@indexer_app.post("/index")
def index_endpoint(request: IndexRequest) -> dict[str, Any]:
    """
    Принимает документы и space_id, "отправляет" их в Core API.
    Пока Core API - это локальный эндпоинт ниже.
    """
    count = _indexer.index_documents(request.space_id, request.documents)
    # В реальном мире здесь был бы HTTP-запрос в отдельный Core API сервис
    return {"indexed": count}


@indexer_app.post("/spaces/{space_id}/ingest")
def ingest_endpoint(
        space_id: str = Path(..., description="Space identifier"),
        request: IngestRequest | None = None,
) -> dict[str, Any]:
    """
    Заглушка Core API: просто логирует входящие документы.
    """
    docs = request.documents if request else []
    _indexer.index_documents(space_id, docs)
    return {"received": len(docs)}
