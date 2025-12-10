from typing import Iterable

import httpx

from indexer_service.models.dto import NormalizedDocument, IngestDocument, IngestPayload


class CoreApiClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def ingest(self, space_id: str, docs: Iterable[NormalizedDocument]) -> int:
        payload = IngestPayload(
            documents=[
                IngestDocument(
                    external_id=d.path,
                    text=d.content,
                    metadata={
                        "source": "local-files",
                        "path": d.path,
                        "chunk_index": idx,
                    },
                )
                for idx, d in enumerate(docs)
            ]
        )

        url = f"{self._base_url}/spaces/{space_id}/ingest"
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload.model_dump())
            resp.raise_for_status()
            data = resp.json()

        # Поток A решит, что именно возвращать (ingested, status и т.п.),
        # мы можем просто попытаться взять "ingested" и fallback на len(payload.documents)
        return int(data.get("ingested", len(payload.documents)))
