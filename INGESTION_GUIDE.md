# Руководство по загрузке данных в RAG систему

## Полный пайплайн индексации

Данные проходят через цепочку микросервисов:

```
Файлы/URL → Scraper → Cleaner → Normalizer → Indexer → Core API → Qdrant
```

### Шаг 1: Scraper Service (порт 8000)
**Что делает:** Читает файлы или скачивает URL

**Endpoint:** `POST http://localhost:8000/api/v1/scrape`

**Пример для файлов:**
```bash
curl -X POST http://localhost:8000/api/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "file_glob": "*.txt"
  }'
```

**Пример для URL:**
```bash
curl -X POST http://localhost:8000/api/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com/article"]
  }'
```

**Ответ:** `RawItem[]` - сырые данные с полем `content`

---

### Шаг 2: Cleaner Service (порт 8001)
**Что делает:** Очищает HTML, нормализует текст

**Endpoint:** `POST http://localhost:8001/clean`

**Пример:**
```bash
curl -X POST http://localhost:8001/clean \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "source": "file",
        "path": "doc1.txt",
        "content": "<p>Hello world</p>"
      }
    ]
  }'
```

**Ответ:** Очищенный текст в поле `cleaned_content`

---

### Шаг 3: Normalizer Service (порт 8002)
**Что делает:** Разбивает текст на чанки, добавляет метаданные

**Endpoint:** `POST http://localhost:8002/normalize`

**Пример:**
```bash
curl -X POST http://localhost:8002/normalize \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "source": "file",
        "path": "doc1.txt",
        "raw_content": "Hello world",
        "cleaned_content": "Hello world"
      }
    ]
  }'
```

**Ответ:** `NormalizedDocument[]` - чанки с метаданными

---

### Шаг 4: Indexer Service (порт 8003)
**Что делает:** Отправляет документы в Core API для индексации

**Endpoint:** `POST http://localhost:8003/index/{space_id}`

**Пример:**
```bash
curl -X POST http://localhost:8003/index/my-space \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "external_id": "file:doc1.txt:0",
        "text": "Hello world",
        "metadata": {
          "source": "file",
          "path": "doc1.txt",
          "title": "Document 1",
          "created_at": "2024-01-01T00:00:00Z",
          "chunk_index": 0,
          "total_chunks": 1
        }
      }
    ]
  }'
```

**Что происходит:** Indexer автоматически вызывает Core API `/spaces/{space_id}/ingest`

---

### Шаг 5: Core API (порт 8004) → Qdrant
**Что делает:** Создаёт эмбеддинги и сохраняет в Qdrant

**Процесс:**
1. Core API получает документы от Indexer
2. Создаёт эмбеддинги через OpenAI Embeddings
3. Сохраняет векторы в Qdrant (коллекция `space_{space_id}`)

---

## Быстрый способ (для тестирования)

Можно напрямую отправить документы в Core API, минуя пайплайн:

```bash
curl -X POST http://localhost:8004/spaces/test-space/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "external_id": "test:doc1:0",
        "text": "Это тестовый документ для проверки RAG системы.",
        "metadata": {
          "source": "file",
          "path": "test.txt",
          "title": "Тестовый документ",
          "created_at": "2024-01-01T00:00:00Z",
          "chunk_index": 0,
          "total_chunks": 1
        }
      }
    ]
  }'
```

---

## Запросы к RAG системе

После индексации можно делать запросы:

```bash
curl -X POST http://localhost:8004/spaces/test-space/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "О чём этот документ?",
    "top_k": 5
  }'
```

**Ответ:**
```json
{
  "answer": "Этот документ описывает...",
  "sources": [
    {
      "text": "Это тестовый документ...",
      "source": "file",
      "path": "test.txt",
      "title": "Тестовый документ"
    }
  ]
}
```

---

## Автоматизация через скрипт

Можно создать скрипт для автоматической индексации всех файлов из `data/docs/`:

```python
# scripts/index_files.py
import httpx

# 1. Scraper
scraper_resp = httpx.post("http://localhost:8000/api/v1/scrape", 
    json={"file_glob": "*.txt"})
raw_items = scraper_resp.json()["items"]

# 2. Cleaner
cleaner_resp = httpx.post("http://localhost:8001/clean",
    json={"items": raw_items})
cleaned = cleaner_resp.json()["items"]

# 3. Normalizer
normalizer_resp = httpx.post("http://localhost:8002/normalize",
    json={"items": cleaned})
docs = normalizer_resp.json()["items"]

# 4. Indexer (автоматически отправляет в Core API)
indexer_resp = httpx.post("http://localhost:8003/index/my-space",
    json={"items": docs})
print(f"Indexed: {indexer_resp.json()['indexed']} documents")
```

---

## Структура данных

### Где хранятся файлы для индексации?
- **Локальные файлы:** `./data/docs/` (монтируется в scraper-service)
- **URL:** передаются напрямую в scraper

### Где хранятся индексированные данные?
- **Qdrant:** коллекции `space_{space_id}` в контейнере qdrant
- **Данные на диске:** `./qdrant_data/` (персистентное хранилище)

---

## Проверка индексированных данных

```bash
# Список коллекций в Qdrant
curl http://localhost:6333/collections

# Информация о коллекции
curl http://localhost:6333/collections/space_test-space

# Количество точек в коллекции
curl http://localhost:6333/collections/space_test-space | jq .result.points_count
```

