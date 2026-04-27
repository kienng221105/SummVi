FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/model-service/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY backend/model-service/app ./app
COPY backend/model-service/ml ./ml

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
