"""
Unit тесты для use case индексации документов.
"""

from unittest.mock import Mock, patch

from core_api.app.handlers.ingest import ingest_documents
from core_api.app.models.dto import IngestItem, IngestRequest, IngestResponse


def test_ingest_empty_documents_returns_zero():
    """Тест: пустой список документов возвращает indexed=0."""
    request = IngestRequest(documents=[])
    result = ingest_documents("test-space", request)
    assert result == IngestResponse(indexed=0)


@patch("core_api.app.handlers.ingest.add_documents_to_index")
@patch("core_api.app.handlers.ingest.documents_to_llama")
def test_ingest_documents_calls_mapper_and_indexer(
        mock_documents_to_llama, mock_add_documents_to_index
):
    """Тест: use case вызывает mapper и indexer с правильными параметрами."""
    # Подготовка
    space_id = "test-space"
    doc1 = IngestItem(
        external_id="doc1",
        text="Test text 1",
        metadata={
            "source": "file",
            "path": "/path/to/file.txt",
            "url": None,
            "title": "Test Document",
            "created_at": "2024-01-01T00:00:00Z",
            "chunk_index": 0,
            "total_chunks": 1,
        },
    )
    doc2 = IngestItem(
        external_id="doc2",
        text="Test text 2",
        metadata={
            "source": "file",
            "path": "/path/to/file2.txt",
            "url": None,
            "title": "Test Document 2",
            "created_at": "2024-01-01T00:00:00Z",
            "chunk_index": 0,
            "total_chunks": 1,
        },
    )
    request = IngestRequest(documents=[doc1, doc2])

    # Моки
    mock_llama_doc1 = Mock()
    mock_llama_doc2 = Mock()
    mock_documents_to_llama.return_value = [mock_llama_doc1, mock_llama_doc2]
    mock_add_documents_to_index.return_value = 2

    # Выполнение
    result = ingest_documents(space_id, request)

    # Проверка
    assert result == IngestResponse(indexed=2)
    mock_documents_to_llama.assert_called_once_with([doc1, doc2])
    mock_add_documents_to_index.assert_called_once_with(space_id, [mock_llama_doc1, mock_llama_doc2])


@patch("core_api.app.handlers.ingest.add_documents_to_index")
@patch("core_api.app.handlers.ingest.documents_to_llama")
def test_ingest_documents_handles_partial_indexing(
        mock_documents_to_llama, mock_add_documents_to_index
):
    """Тест: use case корректно обрабатывает частичную индексацию."""
    space_id = "test-space"
    doc = IngestItem(
        external_id="doc1",
        text="Test text",
        metadata={
            "source": "file",
            "path": "/path/to/file.txt",
            "url": None,
            "title": "Test Document",
            "created_at": "2024-01-01T00:00:00Z",
            "chunk_index": 0,
            "total_chunks": 1,
        },
    )
    request = IngestRequest(documents=[doc])

    mock_llama_doc = Mock()
    mock_documents_to_llama.return_value = [mock_llama_doc]
    # Симулируем, что проиндексирован только 1 из 1 документа
    mock_add_documents_to_index.return_value = 1

    result = ingest_documents(space_id, request)

    assert result == IngestResponse(indexed=1)
