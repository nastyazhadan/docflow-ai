FROM python:3.11-slim

WORKDIR /app

RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app/ui

ENV PYTHONPATH=/app

CMD ["uvicorn", "ui.client_app:app", "--host", "0.0.0.0", "--port", "8000"]


