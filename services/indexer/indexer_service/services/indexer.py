from __future__ import annotations

from typing import Dict, Iterable, List, Any

from indexer_service.models.dto import NormalizedDocument, PipelineContext


def build_ingest_payload(
        *,
        context: PipelineContext,
        items: Iterable[NormalizedDocument],
) -> Dict[str, Any]:
    out_items: List[dict] = []

    for item in items:
        m = item.metadata
        out_items.append(
            {
                "external_id": item.external_id,
                "text": item.text,
                "metadata": {
                    "source": m.source,
                    "path": m.path,
                    "url": m.url,  # ключ присутствует, null допустим
                    "title": m.title,
                    "created_at": m.created_at,
                    "chunk_index": m.chunk_index,
                    "total_chunks": m.total_chunks,
                },
            }
        )

    return {
        "context": context.model_dump(),
        "items": out_items,
    }
