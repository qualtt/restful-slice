#!/bin/bash

set -e # при любой ошибке скрипт ЛЯЖЕТ

# пароли подсасывает из переменных окружения
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- БД
    CREATE DATABASE orders_db;
    CREATE DATABASE inventory_db;

    -- ЮЗЕРЫ (пароли в .env)
    CREATE USER $ORDER_DB_USER WITH ENCRYPTED PASSWORD '$ORDER_DB_PASSWORD';
    CREATE USER $INV_DB_USER WITH ENCRYPTED PASSWORD '$INV_DB_PASSWORD';

    -- ПРАВА
    GRANT ALL PRIVILEGES ON DATABASE orders_db TO $ORDER_DB_USER;
    GRANT ALL PRIVILEGES ON DATABASE inventory_db TO $INV_DB_USER;
EOSQL
