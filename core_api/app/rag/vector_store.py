"""
Управление векторным хранилищем Qdrant для Core API.

Этот модуль отвечает за:
- Подключение к Qdrant
- Создание коллекций для каждого пространства знаний (space_id)
- Работу с векторными индексами через LlamaIndex
"""

import os
from typing import Optional

from llama_index.core import Document as LlamaDocument, StorageContext, VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore  # type: ignore[import-untyped]
from qdrant_client import QdrantClient  # type: ignore[import-untyped]
from qdrant_client.models import Distance, VectorParams  # type: ignore[import-untyped]

# Настройки подключения к Qdrant из переменных окружения
# В Docker Compose QDRANT_HOST будет "qdrant" (имя сервиса)
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"


def get_qdrant_client() -> QdrantClient:
    """
    Создаёт и возвращает клиент для подключения к Qdrant.
    
    Qdrant - векторная БД для хранения эмбеддингов документов.
    Используется для быстрого поиска похожих документов по запросу.
    """
    return QdrantClient(url=QDRANT_URL, prefer_grpc=False)


def get_or_create_collection(space_id: str, client: Optional[QdrantClient] = None) -> str:
    """
    Создаёт коллекцию в Qdrant для указанного пространства знаний, если её нет.
    
    Каждое пространство знаний (space_id) имеет свою коллекцию в Qdrant.
    Это позволяет изолировать данные разных пространств.
    
    Параметры:
    - space_id: идентификатор пространства знаний
    - client: опциональный клиент Qdrant (если не передан, создаётся новый)
    
    Возвращает:
    - Имя коллекции в формате "space_{space_id}"
    """
    qdrant_client: QdrantClient
    if client is None:
        qdrant_client = get_qdrant_client()
    else:
        qdrant_client = client

    # Имя коллекции формируется из space_id для изоляции данных
    collection_name = f"space_{space_id}"

    # Проверяем, существует ли коллекция
    collections = qdrant_client.get_collections().collections
    collection_names = [c.name for c in collections]

    if collection_name not in collection_names:
        # Создаём новую коллекцию с настройками для векторного поиска
        # Используем размерность Ollama embeddings (nomic-embed-text = 768)
        # Можно настроить через переменную окружения EMBEDDING_DIMENSION
        embedding_dim = int(os.getenv("EMBEDDING_DIMENSION", "768"))  # nomic-embed-text размерность
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=embedding_dim,  # Размерность вектора (nomic-embed-text = 768)
                distance=Distance.COSINE,  # Метрика расстояния для поиска (косинусное расстояние)
            ),
        )

    return collection_name


def get_vector_store_index(space_id: str) -> VectorStoreIndex:
    """
    Получает или создаёт VectorStoreIndex для указанного пространства знаний.
    
    VectorStoreIndex - это абстракция LlamaIndex над векторным хранилищем.
    Она предоставляет удобный API для:
    - Добавления документов (автоматически создаёт эмбеддинги)
    - Поиска похожих документов
    - Работы с метаданными
    
    Параметры:
    - space_id: идентификатор пространства знаний
    
    Возвращает:
    - VectorStoreIndex, связанный с коллекцией Qdrant для этого пространства
    """
    client = get_qdrant_client()
    # Убеждаемся, что коллекция существует
    collection_name = get_or_create_collection(space_id, client)

    # Создаём адаптер LlamaIndex для работы с Qdrant
    # Это позволяет LlamaIndex использовать Qdrant как векторное хранилище
    vector_store = QdrantVectorStore(
        collection_name=collection_name,  # Имя коллекции в Qdrant
        client=client,                    # Клиент для подключения к Qdrant
    )

    # StorageContext управляет хранилищем для индекса
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Загружаем существующий индекс или создаём новый
    # Если коллекция пустая, создастся пустой индекс
    # Если в коллекции уже есть документы, они будут доступны через индекс
    try:
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
        )
    except Exception:
        # Если индекс не существует, создаём новый
        # (в большинстве случаев это то же самое, но на всякий случай)
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
        )

    return index


def add_documents_to_index(space_id: str, documents: list[LlamaDocument]) -> int:
    """
    Добавляет документы в векторный индекс для указанного пространства знаний.
    
    Процесс добавления:
    1. Получаем индекс для пространства (или создаём новый)
    2. Для каждого документа:
       - Создаётся эмбеддинг текста (через настроенную embedding модель)
       - Вектор сохраняется в Qdrant вместе с метаданными
       - Документ становится доступным для поиска
    
    Параметры:
    - space_id: идентификатор пространства знаний
    - documents: список документов LlamaIndex для добавления
    
    Возвращает:
    - Количество успешно добавленных документов
    """
    index = get_vector_store_index(space_id)
    # Добавляем документы по одному
    # При добавлении автоматически создаются эмбеддинги и сохраняются в Qdrant
    for doc in documents:
        index.insert(doc)
    return len(documents)

