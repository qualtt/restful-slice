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
    Gateway -->|"GET/POST /api/orders"| OrderSvc["<b>1. Order Service</b><br/><small>Оркестратор заказов</small>"]:::service
    Gateway -->|"GET/POST /api/inventory"| InvSvc["<b>3. Inventory Service</b><br/><small>Склад, пресеты, цены</small>"]:::service

    %% Базы данных (Логическое разделение схем)
    OrderSvc -->|"TCP/IP: orders_schema<br/>Заказы, Пользователи"| PgOrders[("PostgreSQL<br/>(Схема: Orders)")]:::storage
    InvSvc -->|"TCP/IP: inventory_schema<br/>Материалы, Профили, Резервы"| PgInv[("PostgreSQL<br/>(Схема: Inventory)")]:::storage

    %% Работа с файлами (MinIO)
    OrderSvc -->|"S3 API: Сохраняет STL"| Minio[("MinIO / S3<br/><small>Файлы (STL / G-Code)</small>")]:::storage
    
    %% Очереди сообщений (RabbitMQ)
    OrderSvc -->|"AMQP: Публикация задачи<br/>{order_id, file}"| RMQ[["RabbitMQ Broker"]]:::broker
    Worker["<b>2. Slicing Worker</b><br/><small>Воркер нарезки</small>"]:::worker -->|"AMQP: Потребление задач<br/>Подписка на очередь"| RMQ

    %% Возврат результатов нарезки
    Worker -->|"AMQP: Возврат результата<br/>{order_id, weight, time}"| RMQ
    RMQ -->|"AMQP: Чтение результатов"| OrderSvc

    %% Воркер - Файлы и стороннее ПО
    Worker -->|"S3 API: Скачивает STL<br/>Загружает G-code"| Minio
    Worker -->|"CLI / Local Socket"| OrcaSlicer["Orca Slicer"]:::external

    %% Межсервисное взаимодействие (Оркестрация)
    OrderSvc -->|"HTTP/REST (Internal API)<br/>Резерв пластика, запрос цены"| InvSvc

    %% Жизненный цикл заказа (Справочно)
    subgraph Lifecycle [Жизненный цикл заказа]
        direction LR
        L1(pending) --> L2(slicing) --> L3(priced) --> L4(confirmed)
        L4 --> L5(printing) --> L6(completed)
    end
```
## 🧩 Архитектура микросервисов

Проект `restful-slice` (headless-платформа для 3D-печати) состоит из следующих ключевых компонентов. Система построена по принципу оркестрации, где главным управляющим узлом выступает Order Service.

### 1. Order Service (Сервис заказов и Оркестратор)
* **Назначение**: Авторизация пользователей, приём заказов и управление всем их жизненным циклом (Оркестрация бизнес-процесса).
* **Основные функции**:
  * Идентификация клиентов по `X-API-Key`.
  * Прием пользовательских STL файлов (сохраняются в S3/MinIO).
  * Создание сущности заказа и привязка к ней выбранного профиля печати (`profileId`).
  * Публикация задач на "нарезку" (slicing) в брокер очередей (RabbitMQ).
  * **Оркестрация**: Получение результатов от Воркера и вызов внутреннего API (`Internal API`) сервиса склада для резервирования пластика и получения итоговой цены.
  * Выдача текущего статуса заказа клиенту через внешнее API `/api/orders`.

### 2. Slicer Worker (Воркер нарезки)
* **Назначение**: Фоновый, независимый обработчик (stateless consumer). Выполняет исключительно тяжелую математическую операцию конвертации 3D-модели в инструкции для принтера, ничего не зная о бизнес-логике (деньгах, пользователях или складе).
* **Основные функции**:
  * Чтение задач из очередей RabbitMQ.
  * Скачивание исходных STL-файлов из MinIO.
  * Интеграция с движком **Orca Slicer** (через CLI) для генерации G-code.
  * Парсинг логов слайсера для извлечения точного веса затраченного пластика (в граммах) и времени печати.
  * Загрузка итогового G-code обратно в MinIO.
  * **Возврат результатов** нарезки обратно в `Order Service` (через очередь ответов RabbitMQ или внутренний webhook).

### 3. Inventory & Pricing Service (Склад и биллинг)
* **Назначение**: Управление логистикой материалов (филаментов), профилями печати и ценообразованием.
* **Основные функции**:
  * Выдача клиентам списка доступных Профилей Печати (бандл: Принтер + Материал + Настройки качества + Наценка) через внешнее API `/api/inventory/profiles`.
  * Хранение базы физических катушек пластика (цвета, типы, фактические остатки в граммах).
  * **Система резервирования (Internal API)**: По скрытому запросу от `Order Service` проверяет наличие нужного объема пластика, временно "замораживает" (резервирует) его, рассчитывает стоимость печати и возвращает цену оркестратору.
  * Окончательное списание зарезервированного пластика (или возврат на склад при отмене заказа).
 
## ER-диаграмма
```mermaid

erDiagram


    USERS {
        uuid id PK
        varchar username
        varchar api_key "UNIQUE (Ключ авторизации X-API-Key)"
        timestamp created_at
    }

    ORDERS {
        uuid id PK
        uuid user_id FK "Ссылка на USERS.id"
        integer profile_id "ЛОГИЧЕСКАЯ ССЫЛКА на PRINT_PROFILES"
        varchar stl_binary_path "Путь к файлу в MinIO"
        varchar gcode_binary_path "Путь к G-code в MinIO (после нарезки)"
        decimal weight_grams "Вес, рассчитанный воркером"
        integer duration_seconds "Время печати, рассчитанное воркером"
        decimal total_price "Цена, полученная от Inventory API"
        varchar status "pending, slicing, priced, confirmed, printing, completed, failed, cancelled"
        text error_message "Лог ошибки слайсера или нехватки пластика"
        timestamp created_at
        timestamp updated_at
    }


    INVENTORY {
        integer id PK
        varchar label "e.g. Esun PLA White 1kg"
        varchar material_type "PLA, ABS, PETG, TPU"
        decimal total_grams "Фактический (физический) остаток"
        decimal available_grams "Доступно к заказу (total - reserved)"
        decimal cost_per_gram "Себестоимость грамма"
        boolean is_active "default: true"
    }

    MATERIAL_RESERVATIONS {
        uuid id PK
        integer inventory_id FK "Ссылка на конкретную катушку"
        uuid order_id "ЛОГИЧЕСКАЯ ССЫЛКА на ORDERS"
        decimal reserved_grams "Замороженный вес"
        varchar status "reserved (заморожен), consumed (списан), cancelled (возвращен)"
        timestamp created_at
        timestamp updated_at
    }

    PRINTER_PRESETS {
        integer id PK
        varchar model_name "e.g. Creality Ender 3 V2"
        varchar orca_printer_id "Идентификатор для CLI Orca Slicer"
    }

    PROCESS_PRESETS {
        integer id PK
        varchar name "e.g. 0.20mm Standard"
        varchar orca_process_id "Идентификатор для CLI Orca Slicer"
    }

    MATERIAL_PRESETS {
        integer id PK
        varchar name "Название материала для слайсера"
        varchar orca_filament_id "Идентификатор для CLI Orca Slicer"
        integer inventory_id FK "Связь с физической катушкой (Склад)"
    }

    PRINT_PROFILES {
        integer id PK
        varchar display_name "Пресет для юзера: PLA Стандарт (Ender 3)"
        integer printer_id FK
        integer material_id FK
        integer process_id FK
        decimal markup_percent "Коэффициент наценки (e.g. 1.2 = +20%)"
        boolean is_enabled "default: true"
    }
    
    USERS ||--o{ ORDERS : "Создает"
    
    INVENTORY ||--o{ MATERIAL_PRESETS : "Привязывается к пресету"
    INVENTORY ||--o{ MATERIAL_RESERVATIONS : "Хранит резервы"

    PRINTER_PRESETS ||--o{ PRINT_PROFILES : "Включает (Принтер)"
    MATERIAL_PRESETS ||--o{ PRINT_PROFILES : "Включает (Материал)"
    PROCESS_PRESETS ||--o{ PRINT_PROFILES : "Включает (Процесс)"

    
    PRINT_PROFILES ||..o{ ORDERS : "HTTP GET /api/profiles/{id}"
    ORDERS ||..o| MATERIAL_RESERVATIONS : "HTTP POST /api/internal/inventory/reserve"

```

## 🚀 Запуск проекта

### Вариант 1 (Рекомендуемый): Быстрый старт через Docker
Весь проект вместе с базами данных (PostgreSQL), брокером сообщений (RabbitMQ) и S3 хранилищем поднимается с помощью Docker Compose.
```bash
# Поднять всю инфраструктуру в фоне
docker-compose up -d

# Посмотреть логи всех сервисов
docker-compose logs -f
```

