from llama_index.core import Document as LlamaDocument

from core_api.app.rag.mappers import document_to_llama


def test_document_to_llama_with_ingestitem_like_dict():
    doc = {
        "external_id": "doc-1",
        "text": "hello world",
        "metadata": {
            "source": "http",
            "path": None,
            "url": "https://example.com",
            "title": "Example",
            "created_at": "2024-01-01T00:00:00Z",
            "chunk_index": 0,
            "total_chunks": 1,
        },
    }

    llama_doc = document_to_llama(doc)
    assert isinstance(llama_doc, LlamaDocument)
    assert llama_doc.text == "hello world"
    assert llama_doc.metadata["source"] == "http"
    assert llama_doc.metadata["url"] == "https://example.com"
    assert llama_doc.metadata["chunk_index"] == 0
    assert llama_doc.metadata["total_chunks"] == 1


def test_document_to_llama_with_plain_dict_without_metadata():
    # Должно работать даже если metadata отсутствует или является пустым dict
    doc = {
        "external_id": "doc-2",
        "text": "no metadata here",
    }

    llama_doc = document_to_llama(doc)
    assert isinstance(llama_doc, LlamaDocument)
    assert llama_doc.text == "no metadata here"
    # metadata-ключи при отсутствии метаданных будут None
    assert "source" in llama_doc.metadata
    assert llama_doc.metadata["source"] is None


