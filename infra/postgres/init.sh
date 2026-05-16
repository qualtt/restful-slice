#!/bin/sh
# Тонкий wrapper над bootstrap.sql.
# Запускается postgres'ом из /docker-entrypoint-initdb.d/ ТОЛЬКО на первом
# инициализации PGDATA (когда volume пустой). На уже существующем томе postgres
# его не вызовет, поэтому в продакшене ту же самую логику делает Swarm-сервис
# db_bootstrap (см. docker-stack.yml).
#
# Сам SQL — в infra/postgres/bootstrap.sql, единая точка правды.

set -e

: "${ORDER_DB_NAME:=orders_db}"
: "${INV_DB_NAME:=inventory_db}"

psql -v ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname   "$POSTGRES_DB"   \
    --variable=ord_user="$ORDER_DB_USER"     \
    --variable=ord_pass="$ORDER_DB_PASSWORD" \
    --variable=ord_db="$ORDER_DB_NAME"       \
    --variable=inv_user="$INV_DB_USER"       \
    --variable=inv_pass="$INV_DB_PASSWORD"   \
    --variable=inv_db="$INV_DB_NAME"         \
    -f /opt/restful-slice/bootstrap.sql
