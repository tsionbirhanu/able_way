# One image for both servers (see docker-compose.yml):
#   tutor     python server/app.py              the Savanna pages, the <db-assistant> module, /api/...
#   channels  uvicorn server.main:app           Telegram, SMS, /lite, help desk, jobs, teacher view
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

EXPOSE 8000 8001
