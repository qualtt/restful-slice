# Скрипт кладём в образ: bind-mount с хоста (Docker Desktop / macOS) часто даёт
# noexec → «bad interpreter: Permission denied» при запуске из /docker-entrypoint-initdb.d.
FROM postgres:15-alpine
COPY init.sh /docker-entrypoint-initdb.d/10-restful-slice.sh
