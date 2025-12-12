"""
Unit тесты для vector_store модуля.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from core_api.app.rag.vector_store import (
    sanitize_space_id,
    get_or_create_collection,
    get_qdrant_client,
)


def test_sanitize_space_id_allows_valid_chars():
    """Тест: sanitize_space_id разрешает валидные символы."""
    assert sanitize_space_id("test-space_123") == "test-space_123"
    assert sanitize_space_id("TestSpace123") == "TestSpace123"
    assert sanitize_space_id("space-123_test") == "space-123_test"


def test_sanitize_space_id_replaces_invalid_chars():
    """Тест: sanitize_space_id заменяет невалидные символы на _."""
    assert sanitize_space_id("test space") == "test_space"
    assert sanitize_space_id("test@space#123") == "test_space_123"
    assert sanitize_space_id("test.space/123") == "test_space_123"
    assert sanitize_space_id("test+space*123") == "test_space_123"
    assert sanitize_space_id("тест-space") == "____-space"  # Кириллица заменяется посимвольно


def test_sanitize_space_id_handles_special_cases():
    """Тест: sanitize_space_id обрабатывает крайние случаи."""
    assert sanitize_space_id("") == ""
    assert sanitize_space_id("___") == "___"
    assert sanitize_space_id("123") == "123"
    assert sanitize_space_id("a-b_c") == "a-b_c"


@patch("core_api.app.rag.vector_store.get_qdrant_client")
def test_get_or_create_collection_uses_sanitized_id(mock_get_client):
    """Тест: get_or_create_collection использует санитизированный space_id."""
    mock_client = Mock()
    mock_get_client.return_value = mock_client
    
    # Мокируем get_collection для симуляции несуществующей коллекции
    mock_client.get_collection.side_effect = Exception("Collection not found")
    
    # Вызываем с space_id, содержащим невалидные символы
    result = get_or_create_collection("test space@123", mock_client)
    
    # Проверяем, что имя коллекции санитизировано
    assert result == "space_test_space_123"
    # Проверяем, что create_collection был вызван с правильным именем
    mock_client.create_collection.assert_called_once()
    call_args = mock_client.create_collection.call_args
    assert call_args[1]["collection_name"] == "space_test_space_123"


@patch("core_api.app.rag.vector_store.get_qdrant_client")
def test_get_or_create_collection_checks_existence_efficiently(mock_get_client):
    """Тест: get_or_create_collection использует get_collection вместо get_collections."""
    mock_client = Mock()
    mock_get_client.return_value = mock_client
    
    # Коллекция существует
    mock_client.get_collection.return_value = Mock()
    
    result = get_or_create_collection("test-space", mock_client)
    
    # Проверяем, что использовался get_collection (не get_collections)
    mock_client.get_collection.assert_called_once_with("space_test-space")
    # Проверяем, что create_collection НЕ был вызван
    mock_client.create_collection.assert_not_called()
    assert result == "space_test-space"


@patch("core_api.app.rag.vector_store.get_qdrant_client")
def test_get_or_create_collection_creates_when_not_exists(mock_get_client):
    """Тест: get_or_create_collection создаёт коллекцию, если её нет."""
    mock_client = Mock()
    mock_get_client.return_value = mock_client
    
    # Коллекция не существует
    mock_client.get_collection.side_effect = Exception("Collection not found")
    
    result = get_or_create_collection("test-space", mock_client)
    
    # Проверяем, что create_collection был вызван
    mock_client.create_collection.assert_called_once()
    call_args = mock_client.create_collection.call_args
    assert call_args[1]["collection_name"] == "space_test-space"
    # Проверяем параметры коллекции
    vectors_config = call_args[1]["vectors_config"]
    assert vectors_config.size == 768  # default embedding dimension
    assert result == "space_test-space"


@patch("core_api.app.rag.vector_store.get_qdrant_client")
def test_get_or_create_collection_uses_cached_client(mock_get_client):
    """Тест: get_or_create_collection использует кэшированный клиент, если не передан."""
    mock_client = Mock()
    mock_get_client.return_value = mock_client
    mock_client.get_collection.return_value = Mock()
    
    # Вызываем без передачи клиента
    result = get_or_create_collection("test-space")
    
    # Проверяем, что get_qdrant_client был вызван
    mock_get_client.assert_called_once()
    assert result == "space_test-space"


def test_get_qdrant_client_is_cached():
    """Тест: get_qdrant_client кэширует клиент."""
    # Очищаем кэш перед тестом
    get_qdrant_client.cache_clear()
    
    client1 = get_qdrant_client()
    client2 = get_qdrant_client()
    
    # Проверяем, что возвращается тот же объект (кэширован)
    assert client1 is client2

