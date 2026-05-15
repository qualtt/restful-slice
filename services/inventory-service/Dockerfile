# --- Этап 0: Базовые настройки ---
FROM python:3.11-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# --- Этап 1: Сборка зависимостей (Builder) ---
FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Этап 2: Локальная разработка (Development) ---
FROM base AS development
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
EXPOSE 8081
CMD sh -c "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8081 --reload"

# --- Этап 3: Продакшен (Production) ---
FROM base AS production
WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser -s /usr/sbin/nologin appuser
COPY --from=builder /opt/venv /opt/venv
COPY . /app/

USER appuser
EXPOSE 8081
CMD sh -c "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8081"
