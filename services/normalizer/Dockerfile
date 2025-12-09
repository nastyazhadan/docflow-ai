FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY normalizer_service ./normalizer_service

ENV PYTHONPATH=/code

CMD ["uvicorn", "normalizer_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
