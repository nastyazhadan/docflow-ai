import pytest
from fastapi.testclient import TestClient

from indexer_service.main import indexer_app
from indexer_service.models.dto import NormalizedDocument, Metadata, PipelineContext
from indexer_service.services.indexer import build_ingest_payload


class _DummyResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = "ok"

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"bad status: {self.status_code}")

    def json(self) -> dict:
        return self._payload


class _DummyAsyncClient:
    def __init__(self) -> None:
        self.last_url = None
        self.last_json = None

    async def post(self, url: str, json: dict) -> _DummyResponse:  # noqa: A002
        self.last_url = url
        self.last_json = json
        return _DummyResponse(200, {"indexed": len(json.get("items", []))})


@pytest.fixture()
def sample_context() -> PipelineContext:
    return PipelineContext(
        space_id="CTX_SPACE",
        tenant_id=None,
        run_id="run-1",
        started_at="2025-12-13T21:12:00Z",
    )


@pytest.fixture()
def sample_doc() -> NormalizedDocument:
    return NormalizedDocument(
        external_id="file:doc.txt:0",
        text="chunk text",
        metadata=Metadata(
            source="file",
            path="doc.txt",
            url=None,
            title="doc.txt",
            created_at="2025-12-10T19:00:00Z",
            chunk_index=0,
            total_chunks=1,
        ),
    )


def test_build_ingest_payload_empty(sample_context: PipelineContext):
    payload = build_ingest_payload(context=sample_context, items=[])

    assert payload["context"]["space_id"] == "CTX_SPACE"
    assert payload["items"] == []


def test_build_ingest_payload_single(sample_context: PipelineContext, sample_doc: NormalizedDocument):
    payload = build_ingest_payload(context=sample_context, items=[sample_doc])

    assert "context" in payload
    assert "items" in payload
    assert len(payload["items"]) == 1

    d0 = payload["items"][0]
    assert d0["external_id"] == "file:doc.txt:0"
    assert d0["text"] == "chunk text"

    meta = d0["metadata"]
    assert meta["source"] == "file"
    assert meta["path"] == "doc.txt"
    assert meta["url"] is None
    assert meta["title"] == "doc.txt"
    assert meta["chunk_index"] == 0
    assert meta["total_chunks"] == 1


def test_build_ingest_payload_multiple_order(sample_context: PipelineContext):
    docs = []
    for i in range(3):
        docs.append(
            NormalizedDocument(
                external_id=f"file:doc.txt:{i}",
                text=f"chunk {i}",
                metadata=Metadata(
                    source="file",
                    path="doc.txt",
                    url=None,
                    title="doc.txt",
                    created_at="2025-12-10T19:00:00Z",
                    chunk_index=i,
                    total_chunks=3,
                ),
            )
        )

    payload = build_ingest_payload(context=sample_context, items=docs)
    out_items = payload["items"]

    assert len(out_items) == 3
    for i, d in enumerate(out_items):
        assert d["external_id"] == f"file:doc.txt:{i}"
        assert d["text"] == f"chunk {i}"
        assert d["metadata"]["chunk_index"] == i
        assert d["metadata"]["total_chunks"] == 3


def test_index_uses_context_space_id_over_path():
    with TestClient(indexer_app) as client:
        dummy = _DummyAsyncClient()
        client.app.state.http_client = dummy

        resp = client.post(
            "/index/PATH_SPACE",
            json={
                "context": {
                    "space_id": "CTX_SPACE",
                    "tenant_id": None,
                    "run_id": "run-1",
                    "started_at": "2025-12-13T21:12:00Z",
                },
                "items": [
                    {
                        "external_id": "file:doc.txt:0",
                        "text": "chunk text",
                        "metadata": {
                            "source": "file",
                            "path": "doc.txt",
                            "url": None,
                            "title": "doc.txt",
                            "created_at": "2025-12-10T19:00:00Z",
                            "chunk_index": 0,
                            "total_chunks": 1,
                        },
                    }
                ],
            },
        )

        assert resp.status_code == 200
        body = resp.json()

        assert body["context"]["space_id"] == "CTX_SPACE"
        assert body["indexed"] == 1

        assert dummy.last_url == "/spaces/CTX_SPACE/ingest"
        assert "context" in dummy.last_json
        assert "items" in dummy.last_json
        assert len(dummy.last_json["items"]) == 1
