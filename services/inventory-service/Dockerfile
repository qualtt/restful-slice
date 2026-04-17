FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Копируем зависимости и сразу ставим (без виртуального окружения, тут оно не нужно)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Нам не нужно копировать код через COPY . . !
# Код будет подсасываться через volume из локальной папки.

EXPOSE 8081

# Включаем --reload! Как только разраб нажмет CTRL+S в редакторе, код обновится в контейнере!
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8081 --reload"]
