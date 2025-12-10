import pytest

from indexer_service.models.dto import NormalizedDocument, Metadata
from indexer_service.services.indexer import build_ingest_payload


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


def test_build_ingest_payload_empty():
    """
    Пограничный случай: пустой список документов.
    """
    payload = build_ingest_payload([])

    assert isinstance(payload, dict)
    assert "documents" in payload
    assert payload["documents"] == []


def test_build_ingest_payload_single():
    """
    Один документ → один элемент в documents, поля мапятся корректно.
    """
    doc = NormalizedDocument(
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

    payload = build_ingest_payload([doc])

    assert "documents" in payload
    docs = payload["documents"]
    assert isinstance(docs, list)
    assert len(docs) == 1

    d0 = docs[0]
    assert d0["external_id"] == "file:doc.txt:0"
    assert d0["text"] == "chunk text"
    assert d0["metadata"]["source"] == "file"
    assert d0["metadata"]["path"] == "doc.txt"
    assert d0["metadata"]["title"] == "doc.txt"
    assert d0["metadata"]["chunk_index"] == 0
    assert d0["metadata"]["total_chunks"] == 1


def test_build_ingest_payload_multiple():
    """
    Несколько документов → несколько элементов, порядок сохраняется.
    """
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

    payload = build_ingest_payload(docs)

    out_docs = payload["documents"]
    assert len(out_docs) == 3
    # Проверяем порядок и пару ключевых полей
    for i, d in enumerate(out_docs):
        assert d["external_id"] == f"file:doc.txt:{i}"
        assert d["text"] == f"chunk {i}"
        assert d["metadata"]["chunk_index"] == i
        assert d["metadata"]["total_chunks"] == 3
