import pytest
from pydantic import ValidationError

from models import (
    SourceType,
    RawItem,
    CleanItem,
    NormalizedDocument,
    NormalizedDocumentMetadata,
    IngestRequest,
)


def test_raw_item_file_ok():
    item = RawItem(
        source=SourceType.FILE,
        path="data/doc1.md",
        content="# Header\nText",
    )

    assert item.source == SourceType.FILE
    assert item.path == "data/doc1.md"
    assert item.url is None
    assert item.content.startswith("# Header")


def test_raw_item_http_ok():
    item = RawItem(
        source=SourceType.HTTP,
        url="https://example.com/page",
        content="<html><body>Hello</body></html>",
    )

    assert item.source == SourceType.HTTP
    assert str(item.url) == "https://example.com/page"
    assert item.path is None


def test_raw_item_file_without_path_raises():
    with pytest.raises(ValidationError):
        RawItem(
            source=SourceType.FILE,
            content="some content",
        )


def test_raw_item_http_without_url_raises():
    with pytest.raises(ValidationError):
        RawItem(
            source=SourceType.HTTP,
            content="<html></html>",
        )


def test_clean_item_minimal_file_ok():
    item = CleanItem(
        source=SourceType.FILE,
        original_path="data/doc1.md",
        cleaned_text="Clean text",
    )

    assert item.source == SourceType.FILE
    assert item.url is None
    assert item.title is None
    assert item.cleaned_text == "Clean text"


def test_clean_item_minimal_http_ok():
    item = CleanItem(
        source=SourceType.HTTP,
        url="https://example.com",
        cleaned_text="Hello world",
        title="Example",
    )

    assert item.source == SourceType.HTTP
    assert str(item.url) == "https://example.com/"
    assert item.title == "Example"


def test_normalized_document_metadata_chunk_index_non_negative():
    with pytest.raises(ValidationError):
        NormalizedDocumentMetadata(
            source=SourceType.FILE,
            original_path="data/doc1.md",
            chunk_index=-1,
        )


def test_normalized_document_roundtrip():
    meta = NormalizedDocumentMetadata(
        source=SourceType.HTTP,
        url="https://example.com/page",
        title="Example page",
        chunk_index=0,
    )

    doc = NormalizedDocument(
        external_id="https://example.com/page#chunk-0",
        text="Some text",
        metadata=meta,
    )

    data = doc.model_dump()
    doc2 = NormalizedDocument(**data)

    assert doc2 == doc
    assert doc2.metadata.chunk_index == 0
    assert str(doc2.metadata.url) == "https://example.com/page"


def test_ingest_request_allows_empty_documents():
    req = IngestRequest()

    assert req.documents == []

    req2 = IngestRequest(documents=[])
    assert req2.documents == []


def test_ingest_request_with_documents():
    meta = NormalizedDocumentMetadata(
        source=SourceType.FILE,
        original_path="data/doc1.md",
        chunk_index=0,
    )

    doc = NormalizedDocument(
        external_id="data/doc1.md#chunk-0",
        text="Chunk",
        metadata=meta,
    )

    req = IngestRequest(documents=[doc])

    assert len(req.documents) == 1
    assert req.documents[0].external_id == "data/doc1.md#chunk-0"
