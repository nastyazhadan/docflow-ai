"""
Unit тесты для use case выполнения RAG-запросов.
"""

from unittest.mock import Mock, patch

from core_api.app.handlers.query import query_documents
from core_api.app.models.dto import QueryRequest, QueryResponse


@patch("core_api.app.handlers.query.get_vector_store_index")
def test_query_formats_sources_when_source_nodes_present(mock_get_index):
    """Тест: use case корректно форматирует источники, когда source_nodes присутствуют."""
    # Подготовка
    space_id = "test-space"
    request = QueryRequest(query="What is Python?", top_k=3)

    # Моки
    mock_index = Mock()
    mock_query_engine = Mock()
    mock_response = Mock()

    # Настраиваем source_nodes
    mock_node1 = Mock()
    mock_node1.text = "Python is a programming language. " * 10  # > 200 chars
    mock_node1.score = 0.95
    mock_node1.metadata = {"source": "file", "path": "/path/to/doc1.txt", "title": "Python Guide"}

    mock_node2 = Mock()
    mock_node2.text = "Short text"  # < 200 chars
    mock_node2.score = 0.87
    mock_node2.metadata = {"source": "file", "path": "/path/to/doc2.txt"}

    mock_node3 = Mock()
    mock_node3.text = "Another text about Python"
    mock_node3.score = None  # Нет score
    mock_node3.metadata = None  # Нет metadata

    mock_response.source_nodes = [mock_node1, mock_node2, mock_node3]
    mock_response.__str__ = Mock(return_value="Python is a programming language.")

    mock_query_engine.query.return_value = mock_response
    mock_index.as_query_engine.return_value = mock_query_engine
    mock_get_index.return_value = mock_index

    # Выполнение
    result = query_documents(space_id, request)

    # Проверка
    assert isinstance(result, QueryResponse)
    assert result.answer == "Python is a programming language."
    assert len(result.sources) == 3

    # Проверка первого источника (длинный текст обрезан)
    source1 = result.sources[0]
    assert source1.text.endswith("...")
    assert len(source1.text) == 203  # 200 + "..."
    assert source1.score == 0.95
    assert getattr(source1, "source", None) == "file"
    assert getattr(source1, "path", None) == "/path/to/doc1.txt"
    assert getattr(source1, "title", None) == "Python Guide"

    # Проверка второго источника (короткий текст не обрезан)
    source2 = result.sources[1]
    assert source2.text == "Short text"
    assert source2.score == 0.87
    assert getattr(source2, "source", None) == "file"
    assert getattr(source2, "path", None) == "/path/to/doc2.txt"

    # Проверка третьего источника (нет score и metadata)
    source3 = result.sources[2]
    assert source3.text == "Another text about Python"
    assert source3.score is None
    assert not hasattr(source3, "source") or getattr(source3, "source", None) is None
    assert not hasattr(source3, "path") or getattr(source3, "path", None) is None

    # Проверка вызовов
    mock_get_index.assert_called_once_with(space_id)
    mock_index.as_query_engine.assert_called_once_with(similarity_top_k=3)
    mock_query_engine.query.assert_called_once_with("What is Python?")


@patch("core_api.app.handlers.query.get_vector_store_index")
def test_query_handles_no_source_nodes(mock_get_index):
    """Тест: use case корректно обрабатывает случай, когда source_nodes отсутствуют."""
    space_id = "test-space"
    request = QueryRequest(query="Test question", top_k=5)

    mock_index = Mock()
    mock_query_engine = Mock()
    mock_response = Mock()

    # Нет source_nodes
    mock_response.source_nodes = None
    mock_response.__str__ = Mock(return_value="Test answer")

    mock_query_engine.query.return_value = mock_response
    mock_index.as_query_engine.return_value = mock_query_engine
    mock_get_index.return_value = mock_index

    result = query_documents(space_id, request)

    assert isinstance(result, QueryResponse)
    assert result.answer == "Test answer"
    assert result.sources == []


@patch("core_api.app.handlers.query.get_vector_store_index")
def test_query_handles_empty_source_nodes(mock_get_index):
    """Тест: use case корректно обрабатывает пустой список source_nodes."""
    space_id = "test-space"
    request = QueryRequest(query="Test question", top_k=5)

    mock_index = Mock()
    mock_query_engine = Mock()
    mock_response = Mock()

    mock_response.source_nodes = []
    mock_response.__str__ = Mock(return_value="Test answer")

    mock_query_engine.query.return_value = mock_response
    mock_index.as_query_engine.return_value = mock_query_engine
    mock_get_index.return_value = mock_index

    result = query_documents(space_id, request)

    assert isinstance(result, QueryResponse)
    assert result.answer == "Test answer"
    assert result.sources == []


@patch("core_api.app.handlers.query.get_vector_store_index")
def test_query_uses_correct_top_k(mock_get_index):
    """Тест: use case использует правильный top_k из запроса."""
    space_id = "test-space"
    request = QueryRequest(query="Test question", top_k=10)

    mock_index = Mock()
    mock_query_engine = Mock()
    mock_response = Mock()

    mock_response.source_nodes = []
    mock_response.__str__ = Mock(return_value="Answer")

    mock_query_engine.query.return_value = mock_response
    mock_index.as_query_engine.return_value = mock_query_engine
    mock_get_index.return_value = mock_index

    query_documents(space_id, request)

    # Проверяем, что query engine создан с правильным top_k
    mock_index.as_query_engine.assert_called_once_with(similarity_top_k=10)
