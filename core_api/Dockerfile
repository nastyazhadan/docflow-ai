FROM python:3.11-slim

WORKDIR /app

# Обновляем pip для более быстрой установки
RUN pip install --upgrade pip setuptools wheel

# Копируем requirements и устанавливаем зависимости
# Разделяем на этапы для лучшего кэширования
COPY requirements.txt .

# Устанавливаем базовые зависимости сначала (быстрее)
RUN pip install --no-cache-dir \
    pydantic \
    fastapi \
    uvicorn[standard] \
    httpx \
    requests \
    qdrant-client

# Затем устанавливаем LlamaIndex и его зависимости (дольше, но кэшируется отдельно)
RUN pip install --no-cache-dir \
    llama-index \
    llama-index-llms-ollama \
    llama-index-embeddings-ollama \
    llama-index-vector-stores-qdrant \
    ollama

# Опциональные зависимости для разработки (можно убрать в production)
RUN pip install --no-cache-dir pytest || true

# Копируем код API
COPY core_api/ ./core_api/

# Устанавливаем рабочую директорию для импортов
ENV PYTHONPATH=/app

# Запускаем API
CMD ["uvicorn", "core_api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
