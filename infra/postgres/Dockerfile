# Этот образ используется ТОЛЬКО локальным docker-compose.yml (см. build:).
# На сервере в Swarm крутится vanilla postgres:15-alpine — там DDL применяет
# отдельный сервис db_bootstrap, читающий тот же bootstrap.sql через configs:.
#
# Скрипт кладём в образ: bind-mount с хоста (Docker Desktop / macOS) часто даёт
# noexec → «bad interpreter: Permission denied» при запуске из /docker-entrypoint-initdb.d.
FROM postgres:15-alpine

COPY bootstrap.sql /opt/restful-slice/bootstrap.sql
COPY init.sh       /docker-entrypoint-initdb.d/10-restful-slice.sh
