# Этап 1: Сборка зависимостей (Builder)
FROM python:3.11-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# Создаем виртуальное окружение и ставим пакеты
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Этап 2: Локальная разработка (Development)
FROM python:3.11-slim-bookworm AS development
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# Забираем только установленные зависимости
COPY --from=builder /opt/venv /opt/venv

EXPOSE 8081

# В dev режиме мы полагаемся на volume (код не копируем), запускаем с --reload!
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081", "--reload"]

# Этап 3: Продакшен (Production)
FROM python:3.11-slim-bookworm AS production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# Копируем зависимости
COPY --from=builder /opt/venv /opt/venv

# Безопасность: создаем непривилегированного пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Копируем весь код в контейнер (в проде volumes не будет!)
COPY . /app/
# Даем пользователю права на папку с кодом
RUN chown -R appuser:appuser /app

# Переключаемся на безопасного пользователя
USER appuser

EXPOSE 8081
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081"]
