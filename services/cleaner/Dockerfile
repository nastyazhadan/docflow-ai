FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY cleaner_service ./cleaner_service

ENV PYTHONPATH=/code

CMD ["uvicorn", "cleaner_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
