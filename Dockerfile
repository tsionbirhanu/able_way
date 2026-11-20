# The one Mimi server: the Savanna pages, the <db-assistant> module, /api/..., the help desk,
# Telegram, SMS, /lite, job alerts and the teacher view (see docker-compose.yml).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Runs as an unprivileged user; databases and recorded voice clips go to /app/state (a volume).
RUN useradd --create-home --uid 10001 mimi \
    && mkdir -p /app/state /app/data/tts_cache \
    && chown -R mimi /app/state /app/data/tts_cache
USER mimi

EXPOSE 8000
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
