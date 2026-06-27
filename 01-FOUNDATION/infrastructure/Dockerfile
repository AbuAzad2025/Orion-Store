# Orion API image — staging / production (§18)
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==22.0.0

COPY . .

ENV PYTHONPATH=02-CORE:03-MODELS:04-SERVICES:05-API:06-STOREFRONT:07-ADMIN
ENV FLASK_APP=orion.wsgi:app

RUN chmod +x 01-FOUNDATION/infrastructure/docker-entrypoint.sh

EXPOSE 5000

HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD curl -fsS http://127.0.0.1:5000/health || exit 1

ENTRYPOINT ["01-FOUNDATION/infrastructure/docker-entrypoint.sh"]
