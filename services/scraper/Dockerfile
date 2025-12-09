FROM python:3.11-slim

# Необходимые системные пакеты по минимуму
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники
COPY scraper_service ./scraper_service

# Запуск uvicorn
CMD ["uvicorn", "scraper_service.main:scraper_app", "--host", "0.0.0.0", "--port", "8000"]
