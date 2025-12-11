#!/bin/bash
# Скрипт для запуска всех тестов

set -e

echo "🧪 Запуск тестов DocFlow AI"
echo ""

# Активируем venv если он есть
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Тесты отдельных сервисов
echo "📦 Тесты Scraper Service..."
cd services/scraper
pytest tests/ -v
cd ../..

echo ""
echo "📦 Тесты Cleaner Service..."
cd services/cleaner
pytest tests/ -v
cd ../..

echo ""
echo "📦 Тесты Normalizer Service..."
cd services/normalizer
pytest tests/ -v
cd ../..

echo ""
echo "📦 Тесты Indexer Service..."
cd services/indexer
pytest tests/ -v
cd ../..

echo ""
echo "🔗 Интеграционные тесты (полный пайплайн)..."
cd services/tests_integration
pytest test_ingestion_pipeline.py -v
cd ../..

echo ""
echo "✅ Все тесты завершены!"

