# Этап 1: Сборка зависимостей (Builder)
FROM python:3.11-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Этап 2: Для локальной разработки (Development)
FROM python:3.11-slim-bookworm AS development
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
RUN mkdir -p /temp && chmod 777 /temp
EXPOSE 8080
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]

# Этап 3: Для продакшена (Production)
FROM python:3.11-slim-bookworm AS production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY . /app/
RUN mkdir -p /temp && chown -R appuser:appuser /temp && chown -R appuser:appuser /app

USER appuser

EXPOSE 8080
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
