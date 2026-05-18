# Load balancer на отдельном VPS (VPS-C) перед двумя gateway на двух VPS — Nginx, Ubuntu 22.04 / Debian 12

## Задача в одном предложении

**Один публичный вход (VPS-C)** принимает весь трафик по **80/443** и **балансирует** его между **двумя одинаковыми API/edge gateway** на **VPS-GW1** и **VPS-GW2** (Kong, Traefik, Envoy, Tyk, свой Nginx и т.д.). Дальше каждый gateway уже маршрутизирует запросы к микросервисам / upstream-сервисам как у вас заложено в архитектуре.

> **Другое значение фразы «два gateway»:** если вам нужны **два балансировщика** (для отказоустойчивости входа), а не два gateway за одним LB — см. раздел [Два балансировщика (HA)](#два-балансировщика-ha-опционально) в конце документа.

## Допущения (вводные неполные)

| Параметр | Значение по умолчанию |
|----------|------------------------|
| Домен | `example.com` (и при необходимости `www.example.com`) |
| Порт **gateway** на VPS-GW1 / VPS-GW2 | `8080` TCP, **HTTP** (см. ниже про TLS) |
| Gateway доступны с VPS-C | по **приватным** IP внутри VPC/VLAN; если приватной сети нет — по публичным IP (хуже с точки зрения безопасности и трафика) |
| Протокол **VPS-C → gateway** | HTTP: TLS **завершается на VPS-C** (типичный вариант: один сертификат, проще сопровождать) |
| Софт балансировщика | **Nginx** |

**Почему Nginx, а не HAProxy / Caddy:** один демон закрывает HTTPS + прокси + балансировку; для Let’s Encrypt удобен `certbot --nginx`; документации и примеров больше. **Ограничение:** без Nginx Plus активные периодические `GET /health` к upstream из коробки нет — ниже дано сочетание пассивных проверок и рекомендаций по эндпоинту `/health` на **каждом gateway**.

Замените во всех блоках плейсхолдеры:

- `203.0.113.10` → публичный IP **VPS-C**
- `10.0.0.11` / `10.0.0.12` → приватные (или иные) IP **VPS-GW1** / **VPS-GW2**
- `example.com` → ваш домен
- `8080` → порт, на котором **слушает gateway** (внутренний HTTP listener)

**Готовые файлы в репозитории (копируйте на серверы и правьте плейсхолдеры):**

| Файл | Назначение |
|------|------------|
| `configs/vps-c/nginx/example.com.conf` | Виртуальный хост → `/etc/nginx/sites-available/` |
| `configs/vps-c/nginx/http-proxy-timeouts.snippet.conf` | Таймауты proxy в `http {}` |
| `configs/vps-c/haproxy/haproxy.cfg` | HAProxy: **активные** `GET /health`, баланс `leastconn` |
| `configs/gateway/kong-trusted-ips.env.example` | Переменные Kong для доверия к VPS-C |
| `configs/gateway/traefik-forwarded-headers.yaml.example` | `trustedIPs` Traefik для порта за LB |

---

## (1) Схема трафика

```
Internet :443/:80
    │
    ▼
┌─────────────────┐
│     VPS-C       │  Nginx: TLS termination, балансировка (least_conn)
│  (balancer)     │  Пассивный failover при ошибках upstream
└────────┬────────┘
         │ HTTP → listener gateway (приватная сеть предпочтительна)
    ┌────┴────┐
    ▼         ▼
┌──────────┐ ┌──────────┐
│ VPS-GW1  │ │ VPS-GW2  │  Одинаковый gateway :8080 → ваши сервисы
└──────────┘ └──────────┘
```

Клиент всегда видит только **VPS-C**. Цепочка доверия к IP клиента: **клиент → Nginx (VPS-C) → gateway → приложение** — см. раздел 5 (два прокси-уровня).

---

## (2) Конфиги (VPS-C)

### 2.1 Установка

```bash
sudo apt update
sudo apt install -y nginx
sudo systemctl enable --now nginx
```

### 2.2 Фрагмент `http { ... }` — общие таймауты (опционально)

**Файл:** `/etc/nginx/nginx.conf` — внутри блока `http { ... }` можно добавить (или оставить дефолты и переопределить только в `server`):

```nginx
    # Разумные дефолты для API/веба за reverse proxy
    proxy_connect_timeout 5s;
    proxy_send_timeout    60s;
    proxy_read_timeout    60s;
    send_timeout          60s;
```

### 2.3 Upstream + виртуальный хост

**Файл:** `/etc/nginx/sites-available/example.com.conf`  
Создайте файл и сделайте симлинк:

```bash
sudo ln -sf /etc/nginx/sites-available/example.com.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**Содержимое** (сначала HTTP для выпуска сертификата; после Certbot см. раздел TLS):

```nginx
# Upstream: два gateway; пассивный health — после max_fails подряд неудач узел временно исключается
upstream gateway_backends {
    least_conn;
    server 10.0.0.11:8080 max_fails=3 fail_timeout=30s;
    server 10.0.0.12:8080 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name example.com www.example.com;

    location ^~ /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name example.com www.example.com;

    # После certbot сюда подставятся ssl_certificate и ssl_certificate_key
    # ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    # include /etc/letsencrypt/options-ssl-nginx.conf;
    # ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_http_version 1.1;
        proxy_set_header Connection "";

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host  $host;
        proxy_set_header X-Forwarded-Port  $server_port;

        proxy_next_upstream error timeout http_502 http_503 http_504;
        proxy_next_upstream_tries 3;

        proxy_pass http://gateway_backends;
    }
}
```

**Пояснения:**

- `least_conn` — меньше разброс при долгих запросах, чем у чистого round-robin; для равномерной нагрузки замените на отсутствие директивы балансировки по умолчанию (round-robin) или изучите `hash` для sticky.
- `max_fails` / `fail_timeout` — **пассивная** «проверка»: Nginx помечает узел «недоступным» после нескольких ошибок при реальном трафике.
- `keepalive` к upstream уменьшает число TCP-handshake (нужны `proxy_http_version 1.1` и очистка заголовка `Connection`).

### 2.4 Эндпоинт `/health` на gateway

Чтобы пассивная логика и мониторинг работали предсказуемо:

- На **обоих gateway** (или на маршруте «сквозь» gateway к самому лёгкому сервису) должен быть **`GET /health` → 200** без тяжёлых зависимостей (или используйте уже встроенный health в Kong/Traefik и проксируйте его наружу под фиксированным путём).

Nginx на VPS-C **не делает** периодических активных `GET /health` в OSS-редакции; при недоступности gateway запросы получат 502, после `max_fails` узел временно выпадает из пула. Нужны **активные** проверки без пользовательского трафика — смотрите HAProxy в конце документа или внешний blackbox.

### 2.5 TLS до gateway vs только на VPS-C

| Вариант | Когда уместно | Заметка |
|--------|----------------|--------|
| **TLS только на VPS-C** (рекомендуется в этом гайде) | Один публичный домен, сертификат в одном месте | Между VPS-C и gateway — **HTTP по приватной сети** или с строгим firewall |
| **Gateway уже принимают HTTPS** | Уже выпущены отдельные сертификаты на каждом GW | Либо `proxy_pass https://...` с доверием к внутреннему CA, либо упростить и перевести gateway на plain HTTP за LC |
| **TCP passthrough (без расшифровки на VPS-C)** | Нужен end-to-end TLS до gateway, SNI на бэкенде | Отдельный блок `stream { proxy_pass ... }` в Nginx или HAProxy mode TCP — **вне рамок** текущего HTTP-конфига; потребует отдельной настройки cert на каждом GW |

---

## (3) Firewall

### 3.1 VPS-C (балансировщик)

Разрешить с интернета:

- TCP **80**, **443**

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

### 3.2 VPS-GW1 и VPS-GW2 (два gateway)

**Цель:** порт **gateway** (`8080` или ваш) доступен **только с IP VPS-C** (и при необходимости с bastion / админской подсети для отладки).

Пример: трафик к gateway идёт с машины VPS-C; в публичной сети укажите **публичный** IP VPS-C, в private VLAN — **приватный** IP VPS-C.

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
# Только балансировщик → gateway
sudo ufw allow from 203.0.113.10 to any port 8080 proto tcp
# Опционально: админский VPN / домашний IP
# sudo ufw allow from YOUR_ADMIN_IP to any port 8080 proto tcp
sudo ufw enable
```

SSH не выставляйте на весь интернет без необходимости; лучше ключи, по возможности fail2ban или ограничение по IP.

Если бэкенды слушают на `0.0.0.0`, firewall обязателен. Альтернатива: bind приложения на **приватный** интерфейс, если ОС получает private IP.

---

## (4) TLS: Let’s Encrypt и автопродление

### Вариант A — Certbot с webroot (минимум магии)

```bash
sudo apt install -y certbot
sudo mkdir -p /var/www/certbot
sudo certbot certonly --webroot -w /var/www/certbot -d example.com -d www.example.com
```

Затем в блоке `server` для **443** раскомментируйте/пропишите пути к сертификатам (как в шаблоне выше). Либо используйте плагин nginx ниже.

### Вариант B — Certbot nginx-плагин (удобно)

```bash
sudo apt install -y certbot python3-certbot-nginx
```

Сначала оставьте на **443** только заглушку или закомментируйте ssl-сервер до получения сертификата; проще: поднять только **80** с `location ^~ /.well-known/acme-challenge/` и `certbot certonly --webroot`, затем дописать 443 вручную как в шаблоне — надежно для автоматизации.

Полуавтомат через плагин:

```bash
sudo certbot --nginx -d example.com -d www.example.com
```

**Автопродление:** устанавливается **systemd timer** или cron от пакета:

```bash
systemctl list-timers | grep certbot
sudo certbot renew --dry-run
```

---

## (5) Реальный IP клиента за двумя прокси (VPS-C + gateway)

Цепочка: **клиент → Nginx (VPS-C) → gateway → сервисы**. Модуль/настройки «кто первый прокси» должны это учитывать.

1. **Nginx на VPS-C** (уже в конфиге) передаёт на gateway:
   - `X-Real-IP: <клиент>`
   - `X-Forwarded-For: <клиент>, ...` (длиннее, если клиент уже прислал свой XFF)
   - `X-Forwarded-Proto: https`

2. **Gateway** (Kong, Traefik и т.д.) обычно **дописывает** свой hop в `X-Forwarded-For` и может выставлять свои заголовки. Настройте gateway так, чтобы **дальше по цепочке** в микросервисы уходил **оригинальный** клиентский IP, и чтобы **доверие к заголовкам** было только от **VPS-C** (а не от любого клиента интернета). Конкретные ключи зависят от продукта (Trusted IPs / `trusted_proxies` / `real_ip`).

3. **Финальное приложение** за gateway:
   - Должно читать IP из `X-Forwarded-For` / `X-Real-IP` с учётом **двух** доверенных прокси (**VPS-C** + **локальный gateway**), либо использовать то, что gateway уже нормализует в «один» заголовок.
   - **Не** доверять произвольным `X-Forwarded-For` от пользователя без списка доверенных прокси.

4. Модуль `realip` на **gateway** имеет смысл, если нужно подменить `$remote_addr` на бэкенде на IP клиента; список `set_real_ip_from` должен включать **IP VPS-C** (и при необходимости loopback, если ещё локальный прокси).

---

## (6) Чеклист деплоя по шагам

1. **DNS:** `A` / `AAAA` для `example.com` и `www` → **публичный IP VPS-C**.
2. **VPS-GW1 / VPS-GW2:** развернуть **одинаковую** конфигурацию gateway, listener для приёма от VPS-C (например `:8080`), firewall только с IP VPS-C, локально `curl http://127.0.0.1:8080/health` → 200 (или ваш health-путь).
3. **Сеть:** с VPS-C проверить `curl` на оба gateway по внутренним IP.
4. **VPS-C:** Nginx, `sites-available`, `nginx -t`, `reload`.
5. **TLS:** certbot, ssl в блоке 443, снова проверка и `reload`.
6. **Снаружи:** `curl -I https://example.com`.
7. **Failover:** остановить gateway на VPS-GW1 — трафик должен обслуживаться через VPS-GW2 (возможны краткие 502 до `max_fails`).
8. **Логи / метрики:** VPS-C + оба gateway; алерты по 5xx на входе.

---

## (7) Проверка и отладка (curl)

С **VPS-C** (между машинами):

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://10.0.0.11:8080/health
curl -sS -o /dev/null -w "%{http_code}\n" http://10.0.0.12:8080/health
```

С вашей рабочей станции:

```bash
curl -I https://example.com
curl -sS https://example.com/health -w "\nHTTP_CODE:%{http_code}\n"
```

Проверка заголовков на стороне gateway / downstream (логи gateway или временное логирование в Nginx на VPS-C):

```bash
curl -H "X-Debug: 1" https://example.com/
```

Проверка failover (после остановки gateway на одном из VPS):

```bash
for i in $(seq 1 20); do curl -sS -o /dev/null -w "%{http_code} " https://example.com/; done; echo
```

Ожидание: преимущественно 200; кратковременные 502 возможны до исключения мёртвого gateway из upstream.

---

## Два балансировщика (HA, опционально)

Если вы имели в виду **не** «два gateway за одним VPS-C», а **два входных балансировщика** для отказоустойчивости **самого входа**:

- Обычная схема: **Keepalived + VRRP** (или «плавающий»/failover **публичный IP** у провайдера) — два узла **VPS-C1** и **VPS-C2** делят один виртуальный IP, активен master; при падении — переключение.
- **DNS** с двумя `A` на два балансировщика без общего VIP даёт только round-robin на уровни DNS и **не** instant failover.
- Конфигурация Nginx на обоих узлах должна совпадать (`gateway_backends` те же VPS-GW1 / VPS-GW2); TLS-сертификаты синхронизируются (rsync/ansible) или используется ACME на обоих.

Детали VRRP зависят от хостинга (поддержка multicast/unicast VRRP, ограничения на «лишние» MAC).

---

## Если нужны именно активные HTTP health-checks

Рассмотрите выделенный **HAProxy** на VPS-C с `option httpchk GET /health` и разделением «frontend TLS → backend haproxy local» — это отдельная схема от выбранного здесь Nginx-only. Текущий документ намеренно упрощает стек до одного Nginx.
