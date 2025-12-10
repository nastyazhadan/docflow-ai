from __future__ import annotations

from typing import Iterable, List, Dict

from indexer_service.models.dto import NormalizedDocument


def build_ingest_payload(
        items: Iterable[NormalizedDocument],
) -> Dict[str, List[dict]]:
    """
    Преобразует список документов из normalizer формата в payload для
    Core API /spaces/{id}/ingest.

    Алгоритмическая сложность O(n) по числу документов.
    """
    documents: List[dict] = [item.model_dump() for item in items]
    return {"documents": documents}
