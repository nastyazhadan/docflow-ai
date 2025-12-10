import os

from fastapi import FastAPI

from indexer_service.clients.core_api_client import CoreApiClient
from indexer_service.models.dto import IndexRequest

CORE_API_BASE_URL = os.getenv("CORE_API_BASE_URL", "http://api:8000")

indexer_app = FastAPI(title="Indexer Service", version="0.1.0")

_core_api_client = CoreApiClient(CORE_API_BASE_URL)


@indexer_app.post("/index")
def index_endpoint(request: IndexRequest) -> dict:
    count = _core_api_client.ingest(request.space_id, request.documents)
    return {"indexed": count}
