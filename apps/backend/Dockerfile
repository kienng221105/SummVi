FROM python:3.11-slim

WORKDIR /app

COPY apps/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY apps/backend /app/apps/backend
COPY configs /app/configs
COPY data /app/data
COPY ml /app/ml
COPY warehouse /app/warehouse

ENV PYTHONPATH=/app/apps/backend:/app
ENV CHROMA_PERSIST_DIR=/app/chroma_data
ENV HF_HOME=/app/data/models/cache

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
