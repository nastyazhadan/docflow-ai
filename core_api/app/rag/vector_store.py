"""
Управление векторным хранилищем Qdrant для Core API.

Этот модуль отвечает за:
- Подключение к Qdrant
- Создание коллекций для каждого пространства знаний (по UUID KnowledgeSpace)
- Работу с векторными индексами через LlamaIndex

Коллекции именуются как ks_{knowledge_space_uuid} для гарантированной уникальности
и изоляции данных между tenant'ами.
"""

import logging
import os
import uuid
from functools import lru_cache
from typing import Optional

from llama_index.core import Document as LlamaDocument, StorageContext, VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore  # type: ignore[import-untyped]
from qdrant_client import QdrantClient  # type: ignore[import-untyped]
from qdrant_client.models import Distance, VectorParams  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# Настройки подключения к Qdrant из переменных окружения
# В Docker Compose QDRANT_HOST будет "qdrant" (имя сервиса)
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """
    Создаёт и возвращает кэшированный клиент для подключения к Qdrant.
    
    Qdrant - векторная БД для хранения эмбеддингов документов.
    Используется для быстрого поиска похожих документов по запросу.
    
    Клиент кэшируется для переиспользования между запросами.
    """
    return QdrantClient(url=QDRANT_URL, prefer_grpc=False)


def get_or_create_collection(knowledge_space_id: uuid.UUID, client: Optional[QdrantClient] = None) -> str:
    """
    Создаёт коллекцию в Qdrant для указанного пространства знаний, если её нет.
    
    Каждое пространство знаний (KnowledgeSpace) имеет свою коллекцию в Qdrant.
    Имя коллекции формируется из UUID KnowledgeSpace для гарантированной уникальности
    и изоляции данных между tenant'ами.
    
    Параметры:
    - knowledge_space_id: UUID пространства знаний (KnowledgeSpace.id)
    - client: опциональный клиент Qdrant (если не передан, используется кэшированный)
    
    Возвращает:
    - Имя коллекции в формате "ks_{knowledge_space_uuid}" (UUID без дефисов)
    """
    qdrant_client: QdrantClient
    if client is None:
        qdrant_client = get_qdrant_client()
    else:
        qdrant_client = client

    # Формируем имя коллекции из UUID (без дефисов для совместимости с Qdrant)
    collection_name = f"ks_{knowledge_space_id.hex}"

    # Проверяем существование коллекции через get_collection (более эффективно)
    try:
        qdrant_client.get_collection(collection_name)
        # Коллекция существует
    except Exception:
        # Коллекция не существует, создаём новую
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
        logger.info(
            "[VECTOR_STORE] Created collection %s for knowledge_space_id=%s",
            collection_name,
            knowledge_space_id,
        )

    return collection_name


def get_vector_store_index(knowledge_space_id: uuid.UUID) -> VectorStoreIndex:
    """
    Получает или создаёт VectorStoreIndex для указанного пространства знаний.
    
    VectorStoreIndex - это абстракция LlamaIndex над векторным хранилищем.
    Она предоставляет удобный API для:
    - Добавления документов (автоматически создаёт эмбеддинги)
    - Поиска похожих документов
    - Работы с метаданными
    
    Параметры:
    - knowledge_space_id: UUID пространства знаний (KnowledgeSpace.id)
    
    Возвращает:
    - VectorStoreIndex, связанный с коллекцией Qdrant для этого пространства
    """
    client = get_qdrant_client()
    # Убеждаемся, что коллекция существует
    collection_name = get_or_create_collection(knowledge_space_id, client)
    
    logger.info(
        "[VECTOR_STORE] Getting index for knowledge_space_id=%s collection_name=%s",
        knowledge_space_id,
        collection_name,
    )

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
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
    )
    
    # Проверяем количество точек в коллекции для отладки
    try:
        collection_info = client.get_collection(collection_name)
        points_count = collection_info.points_count
        logger.info(
            "[VECTOR_STORE] Collection %s has %d points",
            collection_name,
            points_count,
        )
    except Exception as e:
        logger.warning(
            "[VECTOR_STORE] Failed to get collection info for %s: %s",
            collection_name,
            e,
        )

    return index


def add_documents_to_index(knowledge_space_id: uuid.UUID, documents: list[LlamaDocument]) -> int:
    """
    Добавляет документы в векторный индекс для указанного пространства знаний.
    
    Процесс добавления:
    1. Получаем индекс для пространства (или создаём новый)
    2. Для каждого документа:
       - Создаётся эмбеддинг текста (через настроенную embedding модель)
       - Вектор сохраняется в Qdrant вместе с метаданными
       - Документ становится доступным для поиска
    
    Параметры:
    - knowledge_space_id: UUID пространства знаний (KnowledgeSpace.id)
    - documents: список документов LlamaIndex для добавления
    
    Возвращает:
    - Количество успешно добавленных документов
    """
    index = get_vector_store_index(knowledge_space_id)
    # Добавляем документы по одному
    # При добавлении автоматически создаются эмбеддинги и сохраняются в Qdrant
    for doc in documents:
        index.insert(doc)
    return len(documents)

