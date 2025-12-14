from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Dict, Any, List

from fastapi.testclient import TestClient

SPACE_ID = "test-space"


def _ctx() -> Dict[str, Any]:
    return {
        "space_id": SPACE_ID,
        "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _b64(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


def _run_pipeline_for_uploaded_files(
        *,
        scraper_client: TestClient,
        cleaner_client: TestClient,
        normalizer_client: TestClient,
        indexer_client: TestClient,
        files: list[dict[str, str]],
) -> Dict[str, Any]:
    """
    Полный прогон:
    scraper (/api/v1/scrape c files) -> cleaner (/clean) -> normalizer (/normalize)
    -> indexer (/index/{space_id})
    """
    context = _ctx()

    scrape_resp = scraper_client.post(
        "/api/v1/scrape",
        json={"context": context, "files": files},
    )
    assert scrape_resp.status_code == 200
    scraped = scrape_resp.json()
    assert scraped["context"]["space_id"] == SPACE_ID

    raw_items: List[Dict[str, Any]] = scraped["items"]
    assert raw_items, "scraper must return at least one item"

    clean_req = {
        "context": context,
        "items": [
            {
                "source": item["source"],
                "path": item.get("path"),
                "url": item.get("url"),
                "content": item["content"],
            }
            for item in raw_items
        ],
    }
    clean_resp = cleaner_client.post("/clean", json=clean_req)
    assert clean_resp.status_code == 200
    cleaned = clean_resp.json()
    assert cleaned["context"]["space_id"] == SPACE_ID

    cleaned_items: List[Dict[str, Any]] = cleaned["items"]
    assert len(cleaned_items) == len(raw_items)

    norm_req = {"context": context, "items": cleaned_items}
    norm_resp = normalizer_client.post("/normalize", json=norm_req)
    assert norm_resp.status_code == 200
    normalized = norm_resp.json()
    assert normalized["context"]["space_id"] == SPACE_ID

    docs: List[Dict[str, Any]] = normalized["items"]
    assert docs, "normalizer must produce at least one document"

    for doc in docs:
        meta = doc["metadata"]
        assert meta["source"]
        assert meta["path"]
        assert 0 <= meta["chunk_index"] < meta["total_chunks"]

    index_req = {"context": context, "items": docs}
    index_resp = indexer_client.post(f"/index/{SPACE_ID}", json=index_req)
    assert index_resp.status_code == 200
    index_data = index_resp.json()

    assert index_data["context"]["space_id"] == SPACE_ID
    assert index_data["indexed"] == len(docs)

    return {
        "raw_items": raw_items,
        "cleaned_items": cleaned_items,
        "documents": docs,
        "index_response": index_data,
    }


def _run_pipeline_for_http(
        *,
        scraper_client: TestClient,
        cleaner_client: TestClient,
        normalizer_client: TestClient,
        indexer_client: TestClient,
        urls: list[str],
) -> Dict[str, Any]:
    """
    Полный прогон:
    scraper (/api/v1/scrape c urls) -> cleaner (/clean) ->
    normalizer (/normalize) -> indexer (/index/{space_id})

    Возвращает словарь с промежуточными данными.
    """
    context = _ctx()

    # 1. scraper
    scrape_resp = scraper_client.post(
        "/api/v1/scrape",
        json={"context": context, "urls": urls},
    )
    assert scrape_resp.status_code == 200
    scraped = scrape_resp.json()
    assert scraped["context"]["space_id"] == SPACE_ID

    raw_items: List[Dict[str, Any]] = scraped["items"]
    assert raw_items, "scraper must return at least one HTTP item"

    # 2. cleaner
    # ВАЖНО: для HTTP path НЕ должен становиться пустой строкой,
    # иначе normalizer воспримет path как заданный и прокинет "" в metadata.path.
    clean_req = {
        "context": context,
        "items": [
            {
                "source": item["source"],
                "path": item.get("path"),  # <-- было: item.get("path") or ""
                "url": item.get("url"),
                "content": item["content"],
            }
            for item in raw_items
        ],
    }
    clean_resp = cleaner_client.post("/clean", json=clean_req)
    assert clean_resp.status_code == 200
    cleaned = clean_resp.json()
    assert cleaned["context"]["space_id"] == SPACE_ID

    cleaned_items: List[Dict[str, Any]] = cleaned["items"]
    assert len(cleaned_items) == len(raw_items)

    # 3. normalizer
    norm_req = {"context": context, "items": cleaned_items}
    norm_resp = normalizer_client.post("/normalize", json=norm_req)
    assert norm_resp.status_code == 200
    normalized = norm_resp.json()
    assert normalized["context"]["space_id"] == SPACE_ID

    docs: List[Dict[str, Any]] = normalized["items"]
    assert docs, "normalizer must produce at least one document"

    for doc in docs:
        meta = doc["metadata"]
        assert meta["source"] == "http"
        assert meta["url"] is not None
        assert meta["path"], "for http meta.path must not be empty (should be URL)"
        assert 0 <= meta["chunk_index"] < meta["total_chunks"]

    # 4. indexer
    index_req = {"context": context, "items": docs}
    index_resp = indexer_client.post(f"/index/{SPACE_ID}", json=index_req)
    assert index_resp.status_code == 200
    index_data = index_resp.json()

    assert index_data["context"]["space_id"] == SPACE_ID
    assert index_data["indexed"] == len(docs)

    return {
        "raw_items": raw_items,
        "cleaned_items": cleaned_items,
        "documents": docs,
        "index_response": index_data,
    }


def test_full_pipeline_single_file(
        scraper_client: TestClient,
        cleaner_client: TestClient,
        normalizer_client: TestClient,
        indexer_client: TestClient,
):
    files = [
        {"name": "doc.txt", "content_b64": _b64("Hello world. This is a test document."), "encoding": "base64"}
    ]

    result = _run_pipeline_for_uploaded_files(
        scraper_client=scraper_client,
        cleaner_client=cleaner_client,
        normalizer_client=normalizer_client,
        indexer_client=indexer_client,
        files=files,
    )

    raw_items = result["raw_items"]
    docs = result["documents"]

    assert len(raw_items) == 1
    assert raw_items[0]["source"] == "file"
    assert raw_items[0]["path"] == "doc.txt"

    meta0 = docs[0]["metadata"]
    assert meta0["source"] == "file"
    assert meta0["path"] == "doc.txt"
    assert meta0["chunk_index"] == 0
    assert 1 <= meta0["total_chunks"] == len(docs)

    from indexer_service.main import indexer_app  # type: ignore[import-untyped]

    calls = getattr(indexer_app.state, "ingest_calls", [])
    assert len(calls) == 1
    call = calls[0]
    assert call["space_id"] == SPACE_ID
    assert len(call["payload"]["items"]) == len(docs)


def test_full_pipeline_multiple_files_chunk_metadata(
        scraper_client: TestClient,
        cleaner_client: TestClient,
        normalizer_client: TestClient,
        indexer_client: TestClient,
):
    long_text = "Sentence one. " + "Sentence two " * 200

    files = [
        {"name": "short.txt", "content_b64": _b64("Short text."), "encoding": "base64"},
        {"name": "long.txt", "content_b64": _b64(long_text), "encoding": "base64"},
    ]

    result = _run_pipeline_for_uploaded_files(
        scraper_client=scraper_client,
        cleaner_client=cleaner_client,
        normalizer_client=normalizer_client,
        indexer_client=indexer_client,
        files=files,
    )

    docs = result["documents"]

    by_path: dict[str, list[dict]] = {}
    for doc in docs:
        path = doc["metadata"]["path"]
        by_path.setdefault(path, []).append(doc)

    for path, chunks in by_path.items():
        total_set = {c["metadata"]["total_chunks"] for c in chunks}
        assert len(total_set) == 1
        total = total_set.pop()
        assert total == len(chunks)

        indices = sorted(c["metadata"]["chunk_index"] for c in chunks)
        assert indices == list(range(total)), f"Invalid chunk_index for {path}"


def test_indexer_boundary_no_items(indexer_client: TestClient):
    from indexer_service.main import indexer_app  # type: ignore[import-untyped]

    resp = indexer_client.post(
        f"/index/{SPACE_ID}",
        json={"context": _ctx(), "items": []},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["context"]["space_id"] == SPACE_ID
    assert data["indexed"] == 0

    calls = getattr(indexer_app.state, "ingest_calls", [])
    assert calls == []
