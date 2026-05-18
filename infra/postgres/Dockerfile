# Этот образ используется ТОЛЬКО локальным docker-compose.yml (см. build:).
# На сервере в Swarm крутится vanilla postgres:15-alpine — там DDL применяет
# отдельный сервис db_bootstrap, читающий тот же bootstrap.sql через configs:.
#
# Скрипт кладём в образ: bind-mount с хоста (Docker Desktop / macOS) часто даёт
# noexec → «bad interpreter: Permission denied» при запуске из /docker-entrypoint-initdb.d.
#
# Upstream postgres:15.18-alpine3.23 тащит старый gosu с HIGH/CRITICAL в Trivy,
# поэтому пересобираем только этот бинарь на свежем Go и оставляем остальной base слой.
FROM golang:1.25-alpine3.23 AS gosu-builder
RUN apk add --no-cache git
RUN git clone --depth 1 --branch 1.19 https://github.com/tianon/gosu.git /src
WORKDIR /src
RUN go build -trimpath -ldflags='-s -w' -o /gosu .

FROM postgres:15.18-alpine3.23
COPY --from=gosu-builder /gosu /usr/local/bin/gosu

COPY bootstrap.sql /opt/restful-slice/bootstrap.sql
COPY init.sh       /docker-entrypoint-initdb.d/10-restful-slice.sh
