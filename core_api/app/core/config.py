"""
Фабрика для настройки LLM и embeddings в LlamaIndex.

Этот модуль отвечает за:
- Настройку LLM (языковой модели) для генерации ответов
- Настройку embedding модели для создания векторных представлений текста
- Чтение конфигурации из переменных окружения

Текущая конфигурация: только Ollama (локально, без OpenAI)
"""

import os
from typing import Literal, cast

from llama_index.core import Settings
from llama_index.embeddings.ollama import OllamaEmbedding  # type: ignore[import-untyped]
from llama_index.llms.ollama import Ollama

# Поддерживаемые провайдеры LLM
# Сейчас используется только Ollama для полностью локальной работы
LLMProvider = Literal["ollama"]


def configure_llm_from_env() -> None:
    """
    Настраивает глобальный LLM и embeddings в LlamaIndex на основании переменных окружения.
    
    Эта функция вызывается при старте приложения (в lifespan).
    Настройки применяются глобально через Settings.llm и Settings.embed_model.
    
    Переменные окружения:
    - LLM_PROVIDER: "ollama" (по умолчанию "ollama", OpenAI не используется)
    - OLLAMA_MODEL: название модели Ollama для LLM (по умолчанию "gemma3:4b")
    - OLLAMA_EMBEDDING_MODEL: название модели Ollama для embeddings (по умолчанию "nomic-embed-text")
    - OLLAMA_BASE_URL: URL Ollama сервера (по умолчанию "http://host.docker.internal:11434")
    
    LLM (Language Model) - используется для генерации ответов на основе контекста.
    Embeddings - используются для создания векторных представлений текста для поиска.
    """
    # Определяем провайдера LLM из переменных окружения
    provider: LLMProvider = cast(LLMProvider, os.getenv("LLM_PROVIDER", "ollama"))

    if provider == "ollama":
        # Настройка Ollama LLM (локальная модель)
        # Ollama должен быть запущен локально или доступен по сети
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
        # Для доступа из Docker контейнера используем host.docker.internal
        # Для локального запуска можно использовать localhost
        base_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
        Settings.llm = Ollama(model=model, base_url=base_url)

        # Используем Ollama embeddings (локально, без необходимости в OpenAI)
        # Модель для embeddings можно указать отдельно
        # nomic-embed-text - хороший выбор для embeddings (768 размерность)
        # У вас уже установлена эта модель
        embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        Settings.embed_model = OllamaEmbedding(
            model_name=embedding_model,
            base_url=base_url,
        )
        print(f"✅ Ollama LLM настроен: {model}")
        print(f"✅ Ollama Embeddings настроены: {embedding_model}")

    else:
        raise ValueError(f"Unsupported LLM_PROVIDER={provider}. Используйте 'ollama' для локальной работы.")
