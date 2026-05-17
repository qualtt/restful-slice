# --- Этап 0: Базовые настройки ---
FROM python:3.11-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

# --- Этап 1: Сборка зависимостей (Builder) ---
FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip uninstall -y pip setuptools wheel

# --- Этап 2: Для локальной разработки (Development) ---
FROM base AS development
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
# В dev-режиме даем полные права на /temp
RUN mkdir -p /temp && chmod 777 /temp
EXPOSE 8080
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]

# --- Этап 3: Для продакшена (Production) ---
FROM base AS production
WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser -s /usr/sbin/nologin appuser
COPY --from=builder /opt/venv /opt/venv

# Создаем папку /temp и отдаем её appuser
RUN mkdir -p /temp && chown appuser:appuser /temp

# Копируем код (он будет read-only для appuser)
COPY . /app/

USER appuser
EXPOSE 8080
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
