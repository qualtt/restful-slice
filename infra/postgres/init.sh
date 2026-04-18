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

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "orders_db" <<-EOSQL
    CREATE TABLE IF NOT EXISTS files (
        file_id UUID PRIMARY KEY,
        filename TEXT NOT NULL,
        size_bytes BIGINT NOT NULL,
        uploaded_at TIMESTAMPTZ NOT NULL
    );

    CREATE TABLE IF NOT EXISTS orders (
        order_id UUID PRIMARY KEY,
        status TEXT NOT NULL,
        file_id UUID NOT NULL REFERENCES files(file_id) ON DELETE RESTRICT,
        profile_id INTEGER NOT NULL,
        slicing_result JSONB,
        error_message TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    );

    GRANT USAGE ON SCHEMA public TO $ORDER_DB_USER;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $ORDER_DB_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $ORDER_DB_USER;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "inventory_db" <<-EOSQL
    CREATE TABLE IF NOT EXISTS inventory (
        material_id INTEGER PRIMARY KEY,
        total_grams NUMERIC(12,2) NOT NULL CHECK (total_grams >= 0)
    );

    CREATE TABLE IF NOT EXISTS reservations (
        order_id TEXT PRIMARY KEY,
        reservation_id UUID NOT NULL,
        material_id INTEGER NOT NULL REFERENCES inventory(material_id) ON DELETE RESTRICT,
        amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    INSERT INTO inventory (material_id, total_grams)
    VALUES
        (1, 2500.0),
        (2, 1500.0)
    ON CONFLICT (material_id) DO NOTHING;

    GRANT USAGE ON SCHEMA public TO $INV_DB_USER;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $INV_DB_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $INV_DB_USER;
EOSQL
