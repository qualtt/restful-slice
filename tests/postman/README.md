# API E2E in Postman

`Postman` здесь используется как оболочка над versioned-коллекциями из репо:

- коллекции можно импортировать в VS Code extension и запускать руками;
- тот же JSON потом можно гонять через `Newman` в CI;
- фикстуры лежат в репо и грузятся в MinIO отдельным скриптом.

## Какие коллекции есть

- [restful-slice-api-e2e.postman_collection.json](/workspaces/restful-slice/tests/postman/restful-slice-api-e2e.postman_collection.json)
  Основной happy-path сценарий `upload -> create -> poll -> priced`.
- [restful-slice-openapi-contract.postman_collection.json](/workspaces/restful-slice/tests/postman/restful-slice-openapi-contract.postman_collection.json)
  Контрактные тесты, разложенные по папкам `Inventory`, `Orders - Upload`, `Orders - Lifecycle`, `Orders - Errors`, `Happy path E2E`.

## Что покрывает коллекция

- `GET /api/inventory/profiles` для проверки доступного профиля печати;
- `POST /api/orders/files` для загрузки тестовой модели;
- `POST /api/orders` для создания заказа;
- polling `GET /api/orders/{orderId}` до terminal state с проверкой, что заказ доходит до `priced`;
- повторное чтение заказа и список заказов со статусом `priced`;
- базовые negative smoke-проверки на `404` и неверный тип файла.

## Какие фикстуры используются

- happy-path модель: [cube.stl](/workspaces/restful-slice/tests/postman/fixtures/cube.stl)
- negative test файл: [not-a-model.txt](/workspaces/restful-slice/tests/postman/fixtures/not-a-model.txt)
- MinIO profile fixtures для `profileId=3`:
- [printer.json](/workspaces/restful-slice/tests/postman/fixtures/profiles/3/printer.json)
- [process.json](/workspaces/restful-slice/tests/postman/fixtures/profiles/3/process.json)
- [filament.json](/workspaces/restful-slice/tests/postman/fixtures/profiles/3/filament.json)

## Подготовка локального стенда

1. Поднимите стек:

```bash
docker compose up --build -d
```

2. Загрузите fixture profiles в MinIO:

```bash
bash infra/scripts/load-fixtures.sh
```

Скрипт зеркалит `tests/postman/fixtures/profiles/` в `s3://3d-models/profiles/...`.

## Если стенд поднят через Docker Swarm

`docker stack deploy` создаёт swarm services, поэтому `infra/scripts/load-fixtures.sh`
не увидит `minio` через `docker compose ps` и не сможет зацепиться за overlay-сеть как
обычный compose-контейнер.

Для сервера со stack deploy используйте отдельный скрипт:

```bash
bash infra/scripts/load-fixtures-stack.sh
```

Если стек развернут не под именем `restful-slice`, передайте имя явно:

```bash
STACK_NAME=my-stack bash infra/scripts/load-fixtures-stack.sh
```

Скрипт создаёт временный swarm service в сети `${STACK_NAME}_backend_net`, ждёт готовности
`minio` и затем зеркалит `tests/postman/fixtures/profiles/` в тот же bucket.

## Как добавить коллекцию в Postman extension for VS Code

1. Откройте боковую панель `Postman` в VS Code.
2. Нажмите `Import`.
3. Выберите папку [tests/postman](/workspaces/restful-slice/tests/postman), если extension даёт импорт директории.

Если удобнее по файлам, импортируйте отдельно:

- [restful-slice-api-e2e.postman_collection.json](/workspaces/restful-slice/tests/postman/restful-slice-api-e2e.postman_collection.json)
- [restful-slice-local.postman_environment.json](/workspaces/restful-slice/tests/postman/restful-slice-local.postman_environment.json)

4. Откройте раздел `Collections` и найдите нужную коллекцию.
5. В селекторе environment справа сверху выберите `restful-slice local`.

Если ваш workspace лежит не в `/workspaces/restful-slice`, поправьте в environment:

- `sampleModelPath`
- `invalidFilePath`

## Как запускать в VS Code extension

Запускайте через `Collection Runner`, потому что happy-path использует повторный запрос для polling.

1. В панели `Collections` кликните по нужной коллекции или по её папке.
2. Нажмите `Run`.
3. В runner выберите:
- `Environment`: `restful-slice local`
- `Folder`: нужную папку, если хотите гонять только часть набора
- `Delay`: `2000 ms`
4. Нажмите `Run`.

Что запускать:

- в `restful-slice-api-e2e`: `Happy path` для основного e2e и `Negative smoke` для быстрых проверок;
- в `restful-slice-openapi-contract`: можно запускать всю коллекцию целиком или отдельно папки `Inventory`, `Orders - Upload`, `Orders - Lifecycle`, `Orders - Errors`, `Happy path E2E`.

Если `Poll order until priced` падает по таймауту, обычно проблема в стенде:

- profile fixtures не загружены в MinIO;
- контейнеры ещё не healthy;
- сломан `slicer_api` или `slicer_adapter`.

## Опционально через Newman

Если `newman` уже установлен локально, можно гонять коллекцию так:

```bash
newman run tests/postman/restful-slice-api-e2e.postman_collection.json \
  --environment tests/postman/restful-slice-local.postman_environment.json \
  --folder "Happy path" \
  --delay-request 2000
```
