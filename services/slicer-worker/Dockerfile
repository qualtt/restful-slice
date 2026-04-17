FROM python:3.11-slim-bookworm

# НЕ ПЛАЧЬ! ЭТО НЕЙРОЗАГЛУШКА РИСУЙ ЧЕ ХОЧЕШЬ МНЕ ПОЕБАТЬ, ТОЛЬКО СКАЖИ ПОТОМ

# Установка системных зависимостей для Orca Slicer (GLib, рендеринг)
RUN apt-get update && apt-get install -y \
    wget libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Скачиваем бинарник Orca Slicer (пример)
RUN wget -O /usr/local/bin/orcaslicer "ССЫЛКА_НА_БИНАРНИК" && \
    chmod +x /usr/local/bin/orcaslicer

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "worker.py"]
