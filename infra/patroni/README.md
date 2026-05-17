# Patroni (Spilo) + HAProxy для Postgres в Docker Swarm

Отдельный stack **`postgres-ha`**: три инстанса **PostgreSQL 15** ( **[Zalando Spilo](https://github.com/zalando/spilo)** ) + Patroni, **кворум etcd (3 члена)** и вход **RW только через текущего primary** — сервис **`pg_haproxy`** на порту **5432** в overlay.

Приложение из stack **`restful-slice`** ходит в **`postgres-ha_pg_haproxy:5432`**.

## Общая overlay-сеть (обязательно)

Стек приложения объявляет **`backend_net`** как **внешнюю** сеть с фиксированным именем **`restful-slice_backend_net`**. Перед первым деплоем на менеджере:

```bash
docker network inspect restful-slice_backend_net >/dev/null 2>&1 \
  || docker network create -d overlay --attachable restful-slice_backend_net
```

Имя сети задайте и в переменной `RESTFUL_BACKEND_NET_NAME`, если хотите использовать другое (тогда синхронно поменяйте `backend_net → name:` в `docker-stack.yml`).

## Разметка нод (строго три разные машины)

| Узел        | Docker label               | etcd | Postgres (Spilo) |
|-------------|----------------------------|------|-------------------|
| Менеджер    | `patroni.member=a`          | ✅ etcd0 на `a` | `patroni_spilo_a` (приоритет лидера 100) |
| Воркер 1    | `patroni.member=b`          | ✅ etcd1 | `patroni_spilo_b` (приоритет 55) |
| Воркер 2    | `patroni.member=c`          | ✅ etcd2 | `patroni_spilo_c` (приоритет 10) |

```bash
docker node update --label-add patroni.member=a ИМЯ_УЗЛА_МЕНЕДЖЕРА
docker node update --label-add patroni.member=b ИМЯ_ВОРКЕРА_1
docker node update --label-add patroni.member=c ИМЯ_ВОРКЕРА_2
```

**Автоматизация разметки:** при провижинге `infra/ansible/setup-base.yml` шаг **9** выставляет `patroni.member` на узлах **manager**, **worker1**, **worker2** (имена должны совпадать с колонкой **HOSTNAME** в `docker node ls` из вашего инвентаря).

**CI:** после `docker stack deploy postgres-ha` job ждёт, пока все сервисы стека станут `1/1`, скриптом `infra/scripts/wait-postgres-ha.sh`; иначе деплой `restful-slice` даже не стартует (меньше «полусломанного» прода).

**Дополнительно:** зона приложения (**`zone=edge/compute`**) должна быть выставлена как у вас в `docker-stack.yml`; на Patroni она не влияет.

**Лидер «по умолчанию»:** Patroni не привязан к роли Swarm-manager; задаётся через тег **`failover_priority`** (Spilo **`PATRONI_TAGS`**). При равномерном старте кластера **наибольший приоритет у члена на `patroni.member=a`** (обычно менеджер), затем **`b`**, затем **`c`**.

Сервис **`pg_haproxy`** закреплён на **`node.role == manager`** (лёгкий прокси; данные там не живут).

## Переменные для Spilo (совпадают с суперпользователем bootstrap)

Под **`postgres_admin`** понимается тот пользователь Postgres, который в `.env`/секретах совпадает с **`POSTGRES_USER`** приложения **`db_bootstrap`** (можно переопределить через отдельные переменные).

```bash
export RESTFUL_BACKEND_NET_NAME='restful-slice_backend_net'
export POSTGRES_SUPERUSER='postgres_admin'          # часто совпадает с POSTGRES_USER
export POSTGRES_SUPERUSER_PASSWORD='*****'

# Альтернатива: см. infra/patroni/stack.env.example
```

Если нужны отдельные креды суперпользователя Postgres в Swarm-only, задаёте в `.env`:

- `POSTGRES_SUPERUSER`
- `POSTGRES_SUPERUSER_PASSWORD`

## Деплой HA-стека

Подставь переменные (как минимум пароль суперпользователя; имя overlay по умолчанию **`restful-slice_backend_net`**, если не задано **`RESTFUL_BACKEND_NET_NAME`**):

```bash
set -a && [ -f .env ] && . ./.env; set +a
export RESTFUL_BACKEND_NET_NAME="${RESTFUL_BACKEND_NET_NAME:-restful-slice_backend_net}"
export POSTGRES_SUPERUSER="${POSTGRES_SUPERUSER:-$POSTGRES_USER}"
export POSTGRES_SUPERUSER_PASSWORD="${POSTGRES_SUPERUSER_PASSWORD:-$POSTGRES_PASSWORD}"
```

Из **корня репозитория** (путь `./haproxy.cfg` задаётся относительно каталога `infra/patroni`):

```bash
infra/scripts/deploy-postgres-ha.sh
# или напрямую:
docker stack deploy --with-registry-auth -c infra/patroni/stack.yml postgres-ha

docker stack services postgres-ha
```

### etcd в `Pending`: «scheduling constraints not satisfied»

Часто это **устаревшая задача** до того, как на ноду добавили **`patroni.member`**. После проверки меток (`docker node inspect … --format '{{json .Spec.Labels}}'`):

```bash
for s in postgres-ha_etcd0 postgres-ha_etcd1 postgres-ha_etcd2; do
  docker service update --force "$s"
done
```

Если не помогло — для нужного члена циклически **`scale=0`** и **`scale=1`** (данные etcd на томах не трогаются; если задача так и ни разу не была `Running`, потерять нечего).

### Образ etcd: `docker.io/bitnami/etcd:… not found`

Тег **`bitnami/etcd:3.5.17`** (и многие старые теги) **больше не отдаются** с Docker Hub — отсюда `failed to resolve reference … not found`. В манифесте используется официальный образ проекта etcd: **`quay.io/coreos/etcd:v3.5.17`** ([документация](https://etcd.io/docs/v3.5/op-guide/container/)).

Перед деплоем на каждую ноду **a / b / c** проверь pull:

```bash
docker pull quay.io/coreos/etcd:v3.5.17
```

Альтернатива того же патча — **`gcr.io/etcd-development/etcd:v3.5.17`** (если у вас есть доступ к Artifact Registry/Google, а до Quay — нет).

Том etcd в стеке смонтирован в **`/etcd-data`** (`ETCD_DATA_DIR`). Если раньше крутился **Bitnami**, старый layout данных в томах может быть несовместим — после остановки стека при необходимости **удали только пустые/тестовые** named volumes etcd и подними заново (см. раздел ниже).

Проверка лидера (любая задача с Spilo или HAProxy на overlay `patroni_int`):

```bash
docker ps -qf name=postgres-ha_patroni_spilo
docker exec -it "$(docker ps -qf name=postgres-ha_patroni_spilo_a | head -1)" bash -lc 'curl -s http://localhost:8008/patroni | head'
```

Клиенты в сети **`restful-slice_backend_net`** подключаются к хосту **`postgres-ha_pg_haproxy`**, порт **5432**.

## Стек приложения `restful-slice`

После наличия сети и запущенных сервисов **`postgres-ha`**: обычный `docker stack deploy -c docker-stack.yml restful-slice` из CI уже подставляет **`DB_HOST` / bootstrap `PGHOST`** на **`postgres-ha_pg_haproxy`**.

Отдельного сервиса **`postgres`** в `docker-stack.yml` больше нет.

## etcd: миграция и пересборка кластера

- В этом манифесте **`ETCD_INITIAL_CLUSTER_STATE=new`**. Если вы **повторно** поднимаете кластер **на тех же томах**, где уже был другой etcd, контейнеры могут отказаться стартовать. Тогда см. официально: пересборка члена etcd / удаление неконсистентных volumes / смена `existing` состояния (ручная операция).
- Переход с **старой одноузловой конфигурации** (один сервис `etcd` один том на менеджере) на три члена надёжнее делать после **остановки** старого стека **`postgres-ha`**, затем удаления **старых** volumes Patroni/etcd и **cold** развёртывания заново или по инструкциям etcd restore.

## Мониторинг

- REST Patroni на каждом Spilo: **`:8008`**.
- HAProxy статистика: **`:7000`** внутри overlay (наружу не пробрасывается).

## Перенос данных со старого одиночного `postgres`

Это описано в более раннем сценарии: **`pg_dump` / `dumpall`** с менеджерского тома **`pg_data`** (если ещё доступен), восстановление на **`postgres-ha_pg_haproxy`**, затем деплой обновлённого приложения. Для уже пустого кластера Spilo после первого успешного деплоя достаточно **`db_bootstrap`** + миграций сервисов.

## Образ и версии

- **PostgreSQL/Patroni:** **`ghcr.io/zalando/spilo-15:3.2-p1`**. Обновление — по [releases Spilo](https://github.com/zalando/spilo/releases).
- **etcd:** **`quay.io/coreos/etcd:v3.5.17`** — тот же минор патча, без Bitnami.
