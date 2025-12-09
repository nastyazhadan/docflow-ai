FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY indexer_service ./indexer_service

ENV PYTHONPATH=/code

CMD ["uvicorn", "indexer_service.main:indexer_app", "--host", "0.0.0.0", "--port", "8000"]
