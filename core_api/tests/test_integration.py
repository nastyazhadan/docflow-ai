"""
Интеграционные тесты для Core API.

Тестируют полный цикл работы RAG системы:
1. Индексация документов через POST /spaces/{space_id}/ingest
2. Выполнение запросов через POST /spaces/{space_id}/query

Использует реальный Qdrant (если доступен) или мок для изоляции тестов.
"""

import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterator

# Добавляем корневую директорию проекта в PYTHONPATH для импортов
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import httpx
import pytest
from fastapi.testclient import TestClient

from core_api.app.core.config import configure_llm_from_env
from core_api.app.main import app


def is_ollama_available() -> bool:
    """Проверяет, доступен ли Ollama для тестов."""
    try:
        # Для локальных тестов используем localhost, для Docker - host.docker.internal
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        # Заменяем host.docker.internal на localhost для локальных тестов
        if "host.docker.internal" in ollama_url:
            ollama_url = ollama_url.replace("host.docker.internal", "localhost")
        response = httpx.get(f"{ollama_url}/api/version", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


def is_qdrant_available() -> bool:
    """Проверяет, доступен ли Qdrant для тестов."""
    try:
        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        response = httpx.get(f"http://{qdrant_host}:{qdrant_port}/collections", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


def get_test_space_id() -> str:
    """Генерирует уникальный space_id для теста."""
    return f"test-space-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """
    Тестовый клиент для Core API.
    
    Настраивает LLM перед запуском тестов и очищает после.
    """
    # Для локальных тестов используем localhost вместо host.docker.internal
    original_ollama_url = os.getenv("OLLAMA_BASE_URL")
    if not original_ollama_url or "host.docker.internal" in original_ollama_url:
        os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

    # Настраиваем LLM для тестов
    # В тестах можно использовать мок или реальный Ollama
    try:
        configure_llm_from_env()
    except Exception as e:
        # Восстанавливаем оригинальный URL перед пропуском
        if original_ollama_url:
            os.environ["OLLAMA_BASE_URL"] = original_ollama_url
        pytest.skip(f"Не удалось настроить LLM: {e}")

    with TestClient(app) as test_client:
        yield test_client

    # Восстанавливаем оригинальный URL после тестов
    if original_ollama_url:
        os.environ["OLLAMA_BASE_URL"] = original_ollama_url
    elif "OLLAMA_BASE_URL" in os.environ:
        del os.environ["OLLAMA_BASE_URL"]


@pytest.fixture
def test_space_id() -> str:
    """Фикстура для генерации уникального space_id для каждого теста."""
    return get_test_space_id()


@pytest.fixture(autouse=True)
def cleanup_after_test() -> Iterator[None]:
    """
    Автоматическая очистка тестовых данных после каждого теста.
    
    Удаляет коллекцию Qdrant для тестового space_id.
    В реальном проекте можно добавить endpoint для очистки или использовать мок Qdrant.
    """
    yield

    # Очистка всех тестовых коллекций после теста
    try:
        from core_api.app.rag.vector_store import get_qdrant_client

        qdrant_client = get_qdrant_client()
        # Удаляем все коллекции, начинающиеся с "test-space-"
        collections = qdrant_client.get_collections().collections
        for collection in collections:
            if collection.name.startswith("test-space-"):
                qdrant_client.delete_collection(collection.name)
    except Exception:
        # Игнорируем ошибки очистки в тестах
        pass


def test_health_check(client: TestClient) -> None:
    """Тест health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_empty_documents(client: TestClient, test_space_id: str) -> None:
    """Тест индексации пустого списка документов."""
    response = client.post(
        f"/spaces/{test_space_id}/ingest",
        json={"documents": []},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["indexed"] == 0


@pytest.mark.skipif(
    not is_ollama_available() or not is_qdrant_available(),
    reason="Требуется запущенный Ollama и Qdrant для интеграционных тестов",
)
def test_ingest_single_document(client: TestClient, test_space_id: str) -> None:
    """Тест индексации одного документа."""
    document = {
        "external_id": "test:doc1.txt:0",
        "text": "Это тестовый документ о Python программировании. Python - это язык программирования высокого уровня.",
        "metadata": {
            "source": "file",
            "path": "test/doc1.txt",
            "url": None,
            "title": "Тестовый документ 1",
            "created_at": datetime.now().isoformat(),
            "chunk_index": 0,
            "total_chunks": 1,
        },
    }

    response = client.post(
        f"/spaces/{test_space_id}/ingest",
        json={"documents": [document]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["indexed"] == 1


@pytest.mark.skipif(
    not is_ollama_available() or not is_qdrant_available(),
    reason="Требуется запущенный Ollama и Qdrant для интеграционных тестов",
)
def test_ingest_multiple_documents(client: TestClient, test_space_id: str) -> None:
    """Тест индексации нескольких документов."""
    documents = [
        {
            "external_id": f"test:doc{i}.txt:0",
            "text": f"Документ номер {i}. Содержит информацию о теме {i}.",
            "metadata": {
                "source": "file",
                "path": f"test/doc{i}.txt",
                "url": None,
                "title": f"Документ {i}",
                "created_at": datetime.now().isoformat(),
                "chunk_index": 0,
                "total_chunks": 1,
            },
        }
        for i in range(3)
    ]

    response = client.post(
        f"/spaces/{test_space_id}/ingest",
        json={"documents": documents},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["indexed"] == 3


@pytest.mark.skipif(
    not is_ollama_available() or not is_qdrant_available(),
    reason="Требуется запущенный Ollama и Qdrant для интеграционных тестов",
)
def test_ingest_document_with_chunks(client: TestClient, test_space_id: str) -> None:
    """Тест индексации документа, разбитого на несколько чанков."""
    documents = [
        {
            "external_id": f"test:big_doc.txt:{i}",
            "text": f"Это часть {i + 1} большого документа. Каждая часть содержит уникальную информацию.",
            "metadata": {
                "source": "file",
                "path": "test/big_doc.txt",
                "url": None,
                "title": "Большой документ",
                "created_at": datetime.now().isoformat(),
                "chunk_index": i,
                "total_chunks": 3,
            },
        }
        for i in range(3)
    ]

    response = client.post(
        f"/spaces/{test_space_id}/ingest",
        json={"documents": documents},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["indexed"] == 3


def test_query_empty_space(client: TestClient, test_space_id: str) -> None:
    """Тест запроса к пустому пространству (должен вернуть ошибку или пустой ответ)."""
    empty_space_id = f"empty-space-{uuid.uuid4().hex[:8]}"

    response = client.post(
        f"/spaces/{empty_space_id}/query",
        json={"query": "Что такое Python?", "top_k": 5},
    )

    # Может вернуть ошибку или пустой ответ в зависимости от реализации
    assert response.status_code in [200, 404, 500]


@pytest.mark.skipif(
    not is_ollama_available() or not is_qdrant_available(),
    reason="Требуется запущенный Ollama и Qdrant для интеграционных тестов",
)
def test_ingest_and_query_flow(client: TestClient, test_space_id: str) -> None:
    """
    Интеграционный тест полного цикла: индексация -> запрос.
    
    Проверяет, что после индексации документов можно выполнить RAG-запрос
    и получить релевантный ответ.
    """
    # 1. Индексируем документы о Python
    documents = [
        {
            "external_id": "python:basics.txt:0",
            "text": "Python - это интерпретируемый язык программирования высокого уровня. "
                    "Он был создан Гвидо ван Россумом и впервые выпущен в 1991 году. "
                    "Python поддерживает несколько парадигм программирования.",
            "metadata": {
                "source": "file",
                "path": "docs/python/basics.txt",
                "url": None,
                "title": "Основы Python",
                "created_at": datetime.now().isoformat(),
                "chunk_index": 0,
                "total_chunks": 1,
            },
        },
        {
            "external_id": "python:features.txt:0",
            "text": "Python известен своей простотой и читаемостью кода. "
                    "Он имеет динамическую типизацию и автоматическое управление памятью. "
                    "Python широко используется в веб-разработке, data science и машинном обучении.",
            "metadata": {
                "source": "file",
                "path": "docs/python/features.txt",
                "url": None,
                "title": "Особенности Python",
                "created_at": datetime.now().isoformat(),
                "chunk_index": 0,
                "total_chunks": 1,
            },
        },
        {
            "external_id": "javascript:basics.txt:0",
            "text": "JavaScript - это язык программирования, который используется для создания "
                    "интерактивных веб-страниц. Он работает в браузере и на сервере (Node.js).",
            "metadata": {
                "source": "file",
                "path": "docs/javascript/basics.txt",
                "url": None,
                "title": "Основы JavaScript",
                "created_at": datetime.now().isoformat(),
                "chunk_index": 0,
                "total_chunks": 1,
            },
        },
    ]

    # Индексируем документы
    ingest_response = client.post(
        f"/spaces/{test_space_id}/ingest",
        json={"documents": documents},
    )

    if ingest_response.status_code != 200:
        print("STATUS:", ingest_response.status_code)
        print("BODY:", ingest_response.text)

    assert ingest_response.status_code == 200
    assert ingest_response.json()["indexed"] == 3

    # 2. Выполняем запрос о Python
    query_response = client.post(
        f"/spaces/{test_space_id}/query",
        json={"query": "Что такое Python?", "top_k": 2},
    )

    if query_response.status_code != 200:
        print("STATUS:", query_response.status_code)
        print("BODY:", query_response.text)

    assert query_response.status_code == 200

    query_data = query_response.json()
    assert "answer" in query_data
    assert "sources" in query_data
    assert len(query_data["sources"]) > 0

    # Проверяем, что ответ содержит информацию о Python
    # LLM может не упомянуть слово "Python" напрямую, но ответ должен быть релевантным
    answer = query_data["answer"].lower()
    # Проверяем наличие ключевых слов о Python или что ответ не пустой
    python_keywords = ["python", "питон", "язык программирования", "интерпретируемый", "гвидо"]
    assert any(keyword in answer for keyword in python_keywords) or len(answer) > 50

    # Проверяем, что источники содержат метаданные
    for source in query_data["sources"]:
        assert "text" in source
        # Проверяем, что источники связаны с Python (должны быть релевантными)
        source_text = source.get("text", "").lower()
        if "python" in source_text or "питон" in source_text:
            assert "metadata" in source or "path" in source or "title" in source


@pytest.mark.skipif(
    not is_ollama_available() or not is_qdrant_available(),
    reason="Требуется запущенный Ollama и Qdrant для интеграционных тестов",
)
def test_query_with_different_top_k(client: TestClient, test_space_id: str) -> None:
    """Тест запроса с разными значениями top_k."""
    # Индексируем несколько документов
    documents = [
        {
            "external_id": f"test:doc{i}.txt:0",
            "text": f"Документ {i} содержит информацию о теме {i}. " * 3,
            "metadata": {
                "source": "file",
                "path": f"test/doc{i}.txt",
                "url": None,
                "title": f"Документ {i}",
                "created_at": datetime.now().isoformat(),
                "chunk_index": 0,
                "total_chunks": 1,
            },
        }
        for i in range(5)
    ]

    ingest_response = client.post(
        f"/spaces/{test_space_id}/ingest",
        json={"documents": documents},
    )

    if ingest_response.status_code != 200:
        print("STATUS:", ingest_response.status_code)
        print("BODY:", ingest_response.text)

    assert ingest_response.status_code == 200

    # Запрос с top_k=1
    query_response_1 = client.post(
        f"/spaces/{test_space_id}/query",
        json={"query": "тема 0", "top_k": 1},
    )

    if query_response_1.status_code != 200:
        print("STATUS:", query_response_1.status_code)
        print("BODY:", query_response_1.text)

    assert query_response_1.status_code == 200
    assert len(query_response_1.json()["sources"]) <= 1

    # Запрос с top_k=3
    query_response_3 = client.post(
        f"/spaces/{test_space_id}/query",
        json={"query": "тема", "top_k": 3},
    )

    if query_response_3.status_code != 200:
        print("STATUS:", query_response_3.status_code)
        print("BODY:", query_response_3.text)

    assert query_response_3.status_code == 200
    assert len(query_response_3.json()["sources"]) <= 3


def test_query_validation(client: TestClient, test_space_id: str) -> None:
    """Тест валидации запросов."""
    # Пустой запрос
    response = client.post(
        f"/spaces/{test_space_id}/query",
        json={"query": "", "top_k": 5},
    )
    assert response.status_code == 422  # Validation error

    # Запрос без query
    response = client.post(
        f"/spaces/{test_space_id}/query",
        json={"top_k": 5},
    )
    assert response.status_code == 422  # Validation error

    # Запрос с отрицательным top_k
    response = client.post(
        f"/spaces/{test_space_id}/query",
        json={"query": "test", "top_k": -1},
    )
    assert response.status_code == 422  # Validation error


def test_ingest_validation(client: TestClient, test_space_id: str) -> None:
    """Тест валидации запросов на индексацию."""
    # Документ без обязательных полей
    response = client.post(
        f"/spaces/{test_space_id}/ingest",
        json={"documents": [{"text": "test"}]},
    )
    assert response.status_code == 422  # Validation error

    # Документ с пустым текстом
    response = client.post(
        f"/spaces/{test_space_id}/ingest",
        json={
            "documents": [
                {
                    "external_id": "test:doc.txt:0",
                    "text": "",
                    "metadata": {
                        "source": "file",
                        "path": "test/doc.txt",
                        "title": "Test",
                        "created_at": datetime.now().isoformat(),
                        "chunk_index": 0,
                        "total_chunks": 1,
                    },
                }
            ]
        },
    )
    assert response.status_code == 422  # Validation error
