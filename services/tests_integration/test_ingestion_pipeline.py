from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

from fastapi.testclient import TestClient

SPACE_ID = "test-space"


def _create_file(root_dir: Path, name: str, content: str) -> Path:
    path = root_dir / name
    path.write_text(content, encoding="utf-8")
    return path


def _run_pipeline_for_files(
        *,
        scraper_root_dir: Path,
        scraper_client: TestClient,
        cleaner_client: TestClient,
        normalizer_client: TestClient,
        indexer_client: TestClient,
        file_patterns: str,
) -> Dict[str, Any]:
    """
    Полный прогон:
    scraper (/api/v1/scrape) -> cleaner (/clean) -> normalizer (/normalize)
    -> indexer (/index/{space_id})

    Возвращает словарь с промежуточными данными для ассертов.
    """
    # 1. scraper
    scrape_resp = scraper_client.post(
        "/api/v1/scrape",
        json={"file_glob": file_patterns},
    )
    assert scrape_resp.status_code == 200
    scraped = scrape_resp.json()
    raw_items: List[Dict[str, Any]] = scraped["items"]
    assert raw_items, "scraper must return at least one item"

    # 2. cleaner
    clean_req = {
        "items": [
            {
                "source": item["source"],
                "path": item["path"],
                "url": item.get("url"),
                "content": item["content"],
            }
            for item in raw_items
        ]
    }
    clean_resp = cleaner_client.post("/clean", json=clean_req)
    assert clean_resp.status_code == 200
    cleaned = clean_resp.json()
    cleaned_items: List[Dict[str, Any]] = cleaned["items"]
    assert len(cleaned_items) == len(raw_items)

    # 3. normalizer
    norm_req = {"items": cleaned_items}
    norm_resp = normalizer_client.post("/normalize", json=norm_req)
    assert norm_resp.status_code == 200
    normalized = norm_resp.json()
    docs: List[Dict[str, Any]] = normalized["items"]
    assert docs, "normalizer must produce at least one document"

    # sanity-check по метаданным
    for doc in docs:
        meta = doc["metadata"]
        assert meta["source"]
        assert meta["path"]
        assert 0 <= meta["chunk_index"] < meta["total_chunks"]

    # 4. indexer
    index_req = {"items": docs}
    index_resp = indexer_client.post(f"/index/{SPACE_ID}", json=index_req)
    assert index_resp.status_code == 200
    index_data = index_resp.json()
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
    # 1. scraper
    scrape_resp = scraper_client.post(
        "/api/v1/scrape",
        json={"urls": urls},
    )
    assert scrape_resp.status_code == 200
    scraped = scrape_resp.json()
    raw_items: List[Dict[str, Any]] = scraped["items"]
    assert raw_items, "scraper must return at least one HTTP item"

    # 2. cleaner
    clean_req = {
        "items": [
            {
                "source": item["source"],
                "path": item.get("path") or "",
                "url": item.get("url"),
                "content": item["content"],
            }
            for item in raw_items
        ]
    }
    clean_resp = cleaner_client.post("/clean", json=clean_req)
    assert clean_resp.status_code == 200
    cleaned = clean_resp.json()
    cleaned_items: List[Dict[str, Any]] = cleaned["items"]
    assert len(cleaned_items) == len(raw_items)

    # 3. normalizer
    norm_req = {"items": cleaned_items}
    norm_resp = normalizer_client.post("/normalize", json=norm_req)
    assert norm_resp.status_code == 200
    normalized = norm_resp.json()
    docs: List[Dict[str, Any]] = normalized["items"]
    assert docs, "normalizer must produce at least one document"

    for doc in docs:
        meta = doc["metadata"]
        assert meta["source"] == "http"
        assert meta["url"] is not None
        assert 0 <= meta["chunk_index"] < meta["total_chunks"]

    # 4. indexer
    index_req = {"items": docs}
    index_resp = indexer_client.post(f"/index/{SPACE_ID}", json=index_req)
    assert index_resp.status_code == 200
    index_data = index_resp.json()
    assert index_data["indexed"] == len(docs)

    return {
        "raw_items": raw_items,
        "cleaned_items": cleaned_items,
        "documents": docs,
        "index_response": index_data,
    }


def test_full_pipeline_single_file(
        scraper_root_dir: Path,
        scraper_client: TestClient,
        cleaner_client: TestClient,
        normalizer_client: TestClient,
        indexer_client: TestClient,
):
    # Arrange: создаём один простой файл
    _create_file(
        scraper_root_dir,
        "doc.txt",
        "Hello world. This is a test document.",
    )

    result = _run_pipeline_for_files(
        scraper_root_dir=scraper_root_dir,
        scraper_client=scraper_client,
        cleaner_client=cleaner_client,
        normalizer_client=normalizer_client,
        indexer_client=indexer_client,
        file_patterns="*.txt",
    )

    raw_items = result["raw_items"]
    docs = result["documents"]

    # scraper вернул 1 файл
    assert len(raw_items) == 1
    assert raw_items[0]["source"] == "file"
    assert raw_items[0]["path"] == "doc.txt"

    # normalizer вернул >=1 чанка, проверяем базовую целостность метаданных
    meta0 = docs[0]["metadata"]
    assert meta0["source"] == "file"
    assert meta0["path"] == "doc.txt"
    assert meta0["chunk_index"] == 0
    assert 1 <= meta0["total_chunks"] == len(docs)

    # indexer должен был вызвать Core ingest ровно 1 раз
    from indexer_service.main import indexer_app

    calls = getattr(indexer_app.state, "ingest_calls", [])
    assert len(calls) == 1
    call = calls[0]
    assert call["space_id"] == SPACE_ID
    assert len(call["payload"]["documents"]) == len(docs)


def test_full_pipeline_multiple_files_chunk_metadata(
        scraper_root_dir: Path,
        scraper_client: TestClient,
        cleaner_client: TestClient,
        normalizer_client: TestClient,
        indexer_client: TestClient,
):
    # Два файла с разной длиной, чтобы были разные количества чанков
    _create_file(
        scraper_root_dir,
        "short.txt",
        "Short text.",
    )

    long_text = "Sentence one. " + "Sentence two " * 200
    _create_file(
        scraper_root_dir,
        "long.txt",
        long_text,
    )

    result = _run_pipeline_for_files(
        scraper_root_dir=scraper_root_dir,
        scraper_client=scraper_client,
        cleaner_client=cleaner_client,
        normalizer_client=normalizer_client,
        indexer_client=indexer_client,
        file_patterns="*.txt",
    )

    docs = result["documents"]

    # Группируем чанки по path
    by_path: dict[str, list[dict]] = {}
    for doc in docs:
        path = doc["metadata"]["path"]
        by_path.setdefault(path, []).append(doc)

    # Для каждого файла:
    for path, chunks in by_path.items():
        # total_chunks должен быть одинаковым у всех чанков этого файла
        total_set = {c["metadata"]["total_chunks"] for c in chunks}
        assert len(total_set) == 1
        total = total_set.pop()
        assert total == len(chunks)

        # chunk_index должен покрывать диапазон [0, total_chunks-1] без дырок
        indices = sorted(c["metadata"]["chunk_index"] for c in chunks)
        assert indices == list(range(total)), f"Invalid chunk_index for {path}"


def test_indexer_boundary_no_items(indexer_client: TestClient):
    from indexer_service.main import indexer_app

    # Передаём пустой список items → должно вернуть indexed=0
    resp = indexer_client.post(
        f"/index/{SPACE_ID}",
        json={"items": []},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["indexed"] == 0

    # И при этом Core ingest вызываться не должен
    calls = getattr(indexer_app.state, "ingest_calls", [])
    assert calls == []
