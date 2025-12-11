#!/usr/bin/env python3
"""
Быстрый скрипт для индексации файлов в RAG систему.

Использование:
    python scripts/quick_index.py my-space "*.txt"
    python scripts/quick_index.py my-space "*.md"
"""

import sys
import httpx
from typing import List, Dict, Any


def run_pipeline(space_id: str, file_pattern: str) -> Dict[str, Any]:
    """
    Запускает полный пайплайн индексации:
    scraper → cleaner → normalizer → indexer → core API
    """
    print(f"🚀 Начинаем индексацию в пространство '{space_id}' с паттерном '{file_pattern}'...")
    
    # Шаг 1: Scraper - читаем файлы
    print("\n1️⃣ Scraper: читаем файлы...")
    scraper_resp = httpx.post(
        "http://localhost:8000/api/v1/scrape",
        json={"file_glob": file_pattern},
        timeout=30.0,
    )
    scraper_resp.raise_for_status()
    raw_items = scraper_resp.json()["items"]
    print(f"   ✅ Найдено {len(raw_items)} файлов")
    
    if not raw_items:
        print("   ⚠️  Нет файлов для индексации")
        return {"indexed": 0}
    
    # Шаг 2: Cleaner - очищаем текст
    print("\n2️⃣ Cleaner: очищаем текст...")
    clean_req = {
        "items": [
            {
                "source": item["source"],
                "path": item["path"],
                "url": item.get("url"),
                "content": item["content"],
            }
            for item in raw_items
        ]
    }
    cleaner_resp = httpx.post(
        "http://localhost:8001/clean",
        json=clean_req,
        timeout=30.0,
    )
    cleaner_resp.raise_for_status()
    cleaned_items = cleaner_resp.json()["items"]
    print(f"   ✅ Очищено {len(cleaned_items)} документов")
    
    # Шаг 3: Normalizer - разбиваем на чанки
    print("\n3️⃣ Normalizer: разбиваем на чанки...")
    normalizer_resp = httpx.post(
        "http://localhost:8002/normalize",
        json={"items": cleaned_items},
        timeout=60.0,
    )
    normalizer_resp.raise_for_status()
    docs = normalizer_resp.json()["items"]
    print(f"   ✅ Создано {len(docs)} чанков")
    
    # Шаг 4: Indexer - отправляем в Core API
    print(f"\n4️⃣ Indexer: отправляем в Core API (пространство '{space_id}')...")
    indexer_resp = httpx.post(
        f"http://localhost:8003/index/{space_id}",
        json={"items": docs},
        timeout=120.0,
    )
    indexer_resp.raise_for_status()
    result = indexer_resp.json()
    indexed = result["indexed"]
    
    print(f"\n✅ Готово! Проиндексировано {indexed} документов в пространство '{space_id}'")
    print(f"\n💡 Теперь можно делать запросы:")
    print(f"   curl -X POST http://localhost:8004/spaces/{space_id}/query \\")
    print(f'     -H "Content-Type: application/json" \\')
    print(f'     -d \'{{"query": "Ваш вопрос", "top_k": 5}}\'')
    
    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python scripts/quick_index.py <space_id> <file_pattern>")
        print("Пример: python scripts/quick_index.py my-space '*.txt'")
        sys.exit(1)
    
    space_id = sys.argv[1]
    file_pattern = sys.argv[2]
    
    try:
        run_pipeline(space_id, file_pattern)
    except httpx.HTTPError as e:
        print(f"\n❌ Ошибка HTTP: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)

