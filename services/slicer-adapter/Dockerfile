FROM python:3.11-slim
WORKDIR /app
# Отключаем буферизацию вывода, чтобы логи сразу падали в докер
ENV PYTHONUNBUFFERED=1
COPY main.py .
CMD ["python", "main.py"]
