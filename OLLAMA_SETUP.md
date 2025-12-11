# Настройка Ollama для DocFlow AI

## ⚠️ ОБЯЗАТЕЛЬНО: Установка Ollama перед запуском

**Система работает ТОЛЬКО локально с Ollama. Без Ollama система не запустится!**

---

## Шаг 1: Установка Ollama

1. **Скачайте Ollama:**
   - macOS: https://ollama.com/download/mac
   - Linux: https://ollama.com/download/linux
   - Windows: https://ollama.com/download/windows

2. **Установите и запустите:**
   ```bash
   # Ollama должен быть запущен как сервис
   # На macOS/Linux он запускается автоматически после установки
   # Проверьте:
   curl http://localhost:11434/api/version
   ```

---

## Шаг 2: Установка моделей

**Обязательно установите обе модели:**

```bash
# 1. Модель для LLM (генерация ответов)
ollama pull gemma3:4b

# 2. Модель для embeddings (векторные представления)
ollama pull nomic-embed-text
```

**Проверка установленных моделей:**
```bash
curl http://localhost:11434/api/tags
```

Должны быть видны обе модели:
- `gemma3:4b`
- `nomic-embed-text`

---

## Шаг 3: Проверка работы

```bash
# Тест подключения
curl http://localhost:11434/api/version

# Должен вернуть: {"version":"..."}
```

---

## ✅ После установки Ollama

- ✅ Ollama запущен локально
- ✅ Модель `gemma3:4b` установлена
- ✅ Модель `nomic-embed-text` установлена
- ✅ Подключение из Docker контейнера работает

---

## ⚠️ Важно: Система работает только локально

Для работы индексации документов нужны **embeddings** (векторные представления текста).

**Текущая ситуация:**
- ✅ LLM (генерация ответов) - работает через Ollama
- ❌ Embeddings (индексация) - требуют OpenAI API key

### Решение 1: Установить OpenAI API Key (рекомендуется)

1. Получите API key: https://platform.openai.com/account/api-keys
2. Добавьте в `.env` файл или docker-compose.yml:

```bash
# В .env файле
OPENAI_API_KEY=sk-your-actual-key-here
```

Или в docker-compose.yml:
```yaml
environment:
  - OPENAI_API_KEY=${OPENAI_API_KEY}
```

3. Перезапустите API:
```bash
docker compose restart api
```

### Решение 2: Использовать Ollama embeddings (в разработке)

Можно использовать Ollama для embeddings, но это требует дополнительной настройки.

---

## Тестирование Ollama

### Проверка подключения из контейнера:
```bash
docker compose exec api python3 -c "
from llama_index.llms.ollama import Ollama
llm = Ollama(model='gemma3:4b', base_url='http://host.docker.internal:11434')
print(llm.complete('Hello'))
"
```

### Тест через API (после установки OPENAI_API_KEY):
```bash
# 1. Индексация
curl -X POST http://localhost:8004/spaces/test/ingest \
  -H "Content-Type: application/json" \
  -d '{"documents":[...]}'

# 2. Запрос
curl -X POST http://localhost:8004/spaces/test/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Ваш вопрос", "top_k": 3}'
```

---

## Текущая конфигурация

- **LLM Provider:** Ollama
- **Ollama Model:** gemma3:4b
- **Ollama URL:** http://host.docker.internal:11434
- **Embeddings:** OpenAI (требует API key)

---

## Следующие шаги

1. ✅ Ollama настроен и работает
2. ⏳ Установить OPENAI_API_KEY для embeddings
3. ⏳ Протестировать полный цикл: индексация → запрос

