# Slicer Adapter

Сервис между **RabbitMQ**, **MinIO** и **Orca Slicer API** (`POST /slice`): читает задачи нарезки, скачивает входные файлы из MinIO, вызывает API слайсера, загружает G-code обратно в MinIO и публикует результат в очередь.

Контракт сообщений описан в [`../../docs/asyncapi.yml`](../../docs/asyncapi.yml).

## Поток данных

1. Подписка на очередь **`slicing.jobs`** (одно сообщение за раз, `prefetch_count=1`).
2. Парсинг **`slice.requested`**: в payload обязательны **`minio_paths`** (`stl_file`, `printer_profile`, `process_profile`, `filament_profile`).
3. Скачивание четырёх объектов из MinIO во временный каталог `/temp/<uuid>/`.
4. Вызов Orca: `process_profile` уходит в multipart как **`presetProfile`** (имя поля API).
5. Успех → **`slice.completed`** в **`slicing.results`**; ошибка → **`slice.failed`** (тот же exchange/routing по умолчанию через имя очереди).

HTTP: **`GET /health/live`** — только жив ли worker-thread. **`GET /health/ready`** и алиас **`GET /health`** проверяют RabbitMQ, MinIO, Orca API и состояние воркера. При ошибке ответ **503**.

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `RABBITMQ_URL` | Полный AMQP URL (если задан, остальные поля Rabbit не собираются) |
| `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_HOST`, `RABBITMQ_PORT` | Сборка URL, если `RABBITMQ_URL` пуст |
| `MINIO_ENDPOINT` | Хост:порт, например `minio:9000` |
| `MINIO_ACCESS_KEY` / `MINIO_ROOT_USER` | Ключ доступа |
| `MINIO_SECRET_KEY` / `MINIO_ROOT_PASSWORD` | Секрет |
| `MINIO_BUCKET` / `MINIO_BUCKET_NAME` | Бакет с STL и профилями |
| `MINIO_SECURE` | TLS к MinIO (`true`/`false`, по умолчанию `false`) |
| `ORCA_API_URL` / `SLICER_API_URL` | Базовый URL Orca Slicer API (без `/slice`) |
| `EVENT_SPEC_VERSION` | Версия контракта в исходящих событиях (по умолчанию `1.0.0`) |
| `SERVICE_NAME` | Поле `source` в исходящих событиях (по умолчанию `slicer-adapter`) |

## Локальный запуск

Из каталога `services/slicer-adapter`:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MINIO_ENDPOINT=... MINIO_ACCESS_KEY=... MINIO_SECRET_KEY=... MINIO_BUCKET=...
export RABBITMQ_HOST=... # и т.д.
uvicorn src.main:app --host 0.0.0.0 --port 8080
```

Тесты (pytest):

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```
