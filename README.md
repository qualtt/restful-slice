# restful-slice
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-Framework-05998b?style=flat&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Nginx-Reverse_Proxy-009639?style=flat&logo=nginx&logoColor=white" alt="Nginx"/>
  <img src="https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=flat&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/RabbitMQ-Message_Broker-FF6600?style=flat&logo=rabbitmq&logoColor=white" alt="RabbitMQ"/>
  <img src="https://img.shields.io/badge/MinIO-S3_Storage-C72E49?style=flat&logo=minio&logoColor=white" alt="MinIO"/>
  <img src="https://img.shields.io/badge/Docker-Containerization-2496ED?style=flat&logo=docker&logoColor=white" alt="Docker"/>
</p>

<!-- Блок хипстерства (Инструменты, которые делают вид, что код качественный) -->
<p align="center">
  <img src="https://img.shields.io/badge/Linter-Ruff-D7FF64?style=flat&logo=python&logoColor=black" alt="Ruff"/>
  <img src="https://img.shields.io/badge/Pre--commit-Enabled-fab040?style=flat&logo=pre-commit&logoColor=white" alt="Pre-commit"/>
  <img src="https://img.shields.io/badge/Code_Style-Black-000000?style=flat" alt="Black"/>
</p>

<!-- Блок "Колхоз и Кринж" (То самое жизненное) -->
<p align="center">
  <img src="https://img.shields.io/badge/Maintained%3F-Yes_but_actually_no-red?style=flat" alt="Maintained"/>
  <img src="https://img.shields.io/badge/Works_on-My_Machine-brightgreen?style=flat" alt="Works on my machine"/>
  <img src="https://img.shields.io/badge/Friday_Deploy-Enabled-critical?style=flat&logo=fire" alt="Friday Deploy"/>
  <img src="https://img.shields.io/badge/Powered_by-Coffee_%26_Pain-6F4E37?style=flat" alt="Powered by Coffee and Pain"/>
  <img src="https://img.shields.io/badge/Tests-0%25_Coverage-critical?style=flat" alt="Tests Coverage"/>
</p>

<!-- Лицензия и Версия -->
<p align="center">
  <img src="https://img.shields.io/badge/License-BSD-yellow.svg" alt="License BSD"/>
  <img src="https://img.shields.io/badge/Version-1.0.0--beta_Final_v2-blue" alt="Version"/>
</p>
<p align="center">
  <img src="https://github-readme-stats.vercel.app/api?username=ТВОЙ_НИК&show_icons=true&theme=radical" alt="Stats" />
  <img src="https://github-readme-stats.vercel.app/api/top-langs/?username=ТВОЙ_НИК&layout=compact&theme=visionary" alt="Langs" />
</p>
<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="https://github.com/github-copilot"><img src="https://avatars.githubusercontent.com/u/1234567?v=4" width="100px;" alt=""/><br /><sub><b>GitHub Copilot</b></sub></a><br />🤖</td>
  </tr>
</table>
<!-- markdownlint-enable -->
<!-- prettier-ignore-end -->
<!-- ALL-CONTRIBUTORS-LIST:END -->

### Headless REST application for 3D model processing


```mermaid
graph TD
    %% Стилизация компонентов
    classDef gateway fill:#e2e8f0,stroke:#64748b,stroke-width:2px;
    classDef service fill:#bae6fd,stroke:#0284c7,stroke-width:2px;
    classDef worker fill:#fed7aa,stroke:#ea580c,stroke-width:2px;
    classDef storage fill:#bbf7d0,stroke:#16a34a,stroke-width:2px;
    classDef broker fill:#fbcfe8,stroke:#db2777,stroke-width:2px;
    classDef external fill:#f3f4f6,stroke:#9ca3af,stroke-width:2px,stroke-dasharray: 5 5;

    %% Пользователь и шлюз
    User([Пользователь]) -->|"HTTP REST/JSON"| Gateway["NGINX API Gateway<br/><small>Маршрутизация, балансировка,<br/>client_max_body_size</small>"]:::gateway
    
    %% API Маршруты
    Gateway -->|"GET/POST /api/orders"| OrderSvc["<b>1. Order Service</b><br/><small>Сервис заказов</small>"]:::service
    Gateway -->|"GET/POST /api/inventory"| InvSvc["<b>3. Inventory & Pricing Service</b><br/><small>Склад и биллинг</small>"]:::service

    %% Базы данных
    OrderSvc -->|"TCP/IP: Чтение/Запись<br/>Заказы, Пресеты"| PgOrders[("PostgreSQL: Orders")]:::storage
    InvSvc -->|"TCP/IP: Чтение/Запись<br/>Материалы, Остатки"| PgInv[("PostgreSQL: Inventory")]:::storage

    %% Работа с файлами (MinIO)
    OrderSvc -->|"S3 API: Сохраняет STL"| Minio[("MinIO / S3<br/><small>Файлы (STL / G-Code)</small>")]:::storage
    
    %% Очереди сообщений (RabbitMQ)
    OrderSvc -->|"AMQP: Публикация задачи<br/>{order_id, file}"| RMQ[["RabbitMQ Broker"]]:::broker
    Worker["<b>2. Slicing Worker</b><br/><small>Воркер нарезки</small>"]:::worker -->|"AMQP: Потребление задач<br/>Подписка на очередь"| RMQ

    %% Воркер - Файлы и стороннее ПО
    Worker -->|"S3 API: Скачивает STL<br/>Загружает G-code"| Minio
    Worker -->|"CLI / Local Socket"| OrcaSlicer["Orca Slicer"]:::external

    %% Межсервисное взаимодействие (Воркер -> Инвентарь)
    Worker -->|"HTTP/REST (или gRPC)<br/>Запрос цены, списание пластика"| InvSvc

    %% Жизненный цикл заказа (Справочно)
    subgraph Lifecycle [Жизненный цикл заказа]
        direction LR
        L1(pending) --> L2(slicing) --> L3(priced) --> L4(confirmed)
        L4 --> L5(printing) --> L6(completed)
    end
```
## 🧩 Архитектура микросервисов

Проект `restful-slice` (headless-платформа для 3D-печати) состоит из следующих ключевых компонентов:

### 1. Order Service (Сервис заказов)
* **Назначение**: Прием и управление жизненным циклом заказов на 3D-печать.
* **Основные функции**:
  * Загрузка пользовательских STL файлов (сохраняются в S3/MinIO).
  * Создание сущности заказа и привязка к ней выбранного профиля печати (`presetId`).
  * Публикация задач на "нарезку" (slicing) в брокер очередей (RabbitMQ).
  * Выдача статуса готовности заказа клиенту через `/api/orders`.

### 2. Slicer Worker (Воркер нарезки)
* **Назначение**: Фоновый обработчик (consumer), выполняющий тяжелую математическую операцию конвертации 3D-модели в инструкции для принтера.
* **Основные функции**:
  * Чтение задач из очередей RabbitMQ.
  * Скачивание STL-файлов из MinIO.
  * Интеграция с движком **Orca Slicer** для генерации G-code.
  * Подсчет затраченного пластика и времени, взаимодействие с `Inventory Service` для тарификации.
  * Загрузка итогового G-code обратно в MinIO.

### 3. Inventory & Pricing Service (Склад и биллинг)
* **Назначение**: Управление логистикой материалов (филаментов) и ценообразованием.
* **Основные функции**:
  * Хранение базы пластика (цвета, типы, остатки кг).
  * Калькуляция стоимости печати на основе веса сгенерированного G-code.
  * Списание остатков со склада при подтверждении печати `/api/inventory`.

---

## 🚀 Запуск проекта

### Вариант 1 (Рекомендуемый): Быстрый старт через Docker
Весь проект вместе с базами данных (PostgreSQL), брокером сообщений (RabbitMQ) и S3 хранилищем поднимается с помощью Docker Compose.
```bash
# Поднять всю инфраструктуру в фоне
docker-compose up -d

# Посмотреть логи всех сервисов
docker-compose logs -f
