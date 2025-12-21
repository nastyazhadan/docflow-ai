"""
Unit тесты для vector_store модуля.
"""

import uuid
from unittest.mock import Mock, patch

from core_api.app.rag.vector_store import (
    get_or_create_collection,
    get_qdrant_client,
)


@patch("core_api.app.rag.vector_store.get_qdrant_client")
def test_get_or_create_collection_uses_uuid_hex(mock_get_client):
    """Тест: get_or_create_collection использует UUID hex для имени коллекции."""
    mock_client = Mock()
    mock_get_client.return_value = mock_client
    
    # Мокируем get_collection для симуляции несуществующей коллекции
    mock_client.get_collection.side_effect = Exception("Collection not found")
    
    # Создаём тестовый UUID
    test_uuid = uuid.uuid4()
    
    # Вызываем с UUID
    result = get_or_create_collection(test_uuid, mock_client)
    
    # Проверяем, что имя коллекции формируется из UUID hex
    expected_name = f"ks_{test_uuid.hex}"
    assert result == expected_name
    # Проверяем, что create_collection был вызван с правильным именем
    mock_client.create_collection.assert_called_once()
    call_args = mock_client.create_collection.call_args
    assert call_args[1]["collection_name"] == expected_name


@patch("core_api.app.rag.vector_store.get_qdrant_client")
def test_get_or_create_collection_checks_existence_efficiently(mock_get_client):
    """Тест: get_or_create_collection использует get_collection вместо get_collections."""
    mock_client = Mock()
    mock_get_client.return_value = mock_client
    
    # Коллекция существует
    mock_client.get_collection.return_value = Mock()
    
    test_uuid = uuid.uuid4()
    expected_name = f"ks_{test_uuid.hex}"
    
    result = get_or_create_collection(test_uuid, mock_client)
    
    # Проверяем, что использовался get_collection (не get_collections)
    mock_client.get_collection.assert_called_once_with(expected_name)
    # Проверяем, что create_collection НЕ был вызван
    mock_client.create_collection.assert_not_called()
    assert result == expected_name


@patch("core_api.app.rag.vector_store.get_qdrant_client")
def test_get_or_create_collection_creates_when_not_exists(mock_get_client):
    """Тест: get_or_create_collection создаёт коллекцию, если её нет."""
    mock_client = Mock()
    mock_get_client.return_value = mock_client
    
    # Коллекция не существует
    mock_client.get_collection.side_effect = Exception("Collection not found")
    
    test_uuid = uuid.uuid4()
    expected_name = f"ks_{test_uuid.hex}"
    
    result = get_or_create_collection(test_uuid, mock_client)
    
    # Проверяем, что create_collection был вызван
    mock_client.create_collection.assert_called_once()
    call_args = mock_client.create_collection.call_args
    assert call_args[1]["collection_name"] == expected_name
    # Проверяем параметры коллекции
    vectors_config = call_args[1]["vectors_config"]
    assert vectors_config.size == 768  # default embedding dimension
    assert result == expected_name


@patch("core_api.app.rag.vector_store.get_qdrant_client")
def test_get_or_create_collection_uses_cached_client(mock_get_client):
    """Тест: get_or_create_collection использует кэшированный клиент, если не передан."""
    mock_client = Mock()
    mock_get_client.return_value = mock_client
    mock_client.get_collection.return_value = Mock()
    
    test_uuid = uuid.uuid4()
    expected_name = f"ks_{test_uuid.hex}"
    
    # Вызываем без передачи клиента
    result = get_or_create_collection(test_uuid)
    
    # Проверяем, что get_qdrant_client был вызван
    mock_get_client.assert_called_once()
    assert result == expected_name


def test_get_qdrant_client_is_cached():
    """Тест: get_qdrant_client кэширует клиент."""
    # Очищаем кэш перед тестом
    get_qdrant_client.cache_clear()
    
    client1 = get_qdrant_client()
    client2 = get_qdrant_client()
    
    # Проверяем, что возвращается тот же объект (кэширован)
    assert client1 is client2

