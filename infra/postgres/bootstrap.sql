-- =====================================================================
-- restful-slice DB identity bootstrap (single source of truth).
--
-- Запускается ДВУМЯ потребителями:
--   1) Локальный Compose-образ postgres'а на первом инициализации PGDATA —
--      через тонкий wrapper /docker-entrypoint-initdb.d/10-restful-slice.sh
--      (нужно из-за FUSE/macOS, где bind-mount init-скрипта недоступен).
--   2) Swarm-сервис db_bootstrap на каждом деплое — против уже работающего
--      vanilla postgres'а (см. docker-stack.yml, ключ configs:).
--
-- ПАРАМЕТРЫ (передаются через psql -v):
--   ord_user, ord_pass, ord_db   — креды и имя БД сервиса заказов
--   inv_user, inv_pass, inv_db   — креды и имя БД сервиса инвентаря
--
-- ПРАВИЛО: в основном здесь идентичность (роли / БД / гранты на public).
--   Разрешены только идемпотентные ADD COLUMN / смена OWNER для совместимости
--   со старым деплоем (см. блок ниже про files.object_key): без DROP/TRUNCATE/DELETE.
-- =====================================================================

\set ON_ERROR_STOP on

-- --------------------------- Роли -----------------------------------
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'ord_user', :'ord_pass')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'ord_user')\gexec
ALTER ROLE :"ord_user" WITH LOGIN PASSWORD :'ord_pass';

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'inv_user', :'inv_pass')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'inv_user')\gexec
ALTER ROLE :"inv_user" WITH LOGIN PASSWORD :'inv_pass';

-- --------------------------- Базы -----------------------------------
SELECT format('CREATE DATABASE %I OWNER %I', :'ord_db', :'ord_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'ord_db')\gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'inv_db', :'inv_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'inv_db')\gexec

ALTER DATABASE :"ord_db" OWNER TO :"ord_user";
ALTER DATABASE :"inv_db" OWNER TO :"inv_user";

-- ---------------- Гранты на public для orders_db --------------------
\connect :"ord_db"

ALTER SCHEMA public OWNER TO :"ord_user";
GRANT  ALL ON SCHEMA              public TO :"ord_user";
GRANT  ALL ON ALL TABLES    IN SCHEMA public TO :"ord_user";
GRANT  ALL ON ALL SEQUENCES IN SCHEMA public TO :"ord_user";
ALTER  DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES    TO :"ord_user";
ALTER  DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO :"ord_user";

-- Наследие: таблицы могли быть созданы не :"ord_user" — тогда alembic (под службой
-- заказов) падает с «must be owner of table». Плюс object_key добавляется здесь
-- от суперпользователя; ADD IF NOT EXISTS идempotent.
ALTER TABLE IF EXISTS files           OWNER TO :"ord_user";
ALTER TABLE IF EXISTS orders          OWNER TO :"ord_user";
ALTER TABLE IF EXISTS telemetry_events OWNER TO :"ord_user";
ALTER TABLE IF EXISTS files ADD COLUMN IF NOT EXISTS object_key TEXT;
ALTER TABLE IF EXISTS orders ADD COLUMN IF NOT EXISTS api_key_identity TEXT;
ALTER TABLE IF EXISTS telemetry_events ADD COLUMN IF NOT EXISTS api_key_identity TEXT;

-- ---------------- Гранты на public для inventory_db -----------------
\connect :"inv_db"

ALTER SCHEMA public OWNER TO :"inv_user";
GRANT  ALL ON SCHEMA              public TO :"inv_user";
GRANT  ALL ON ALL TABLES    IN SCHEMA public TO :"inv_user";
GRANT  ALL ON ALL SEQUENCES IN SCHEMA public TO :"inv_user";
ALTER  DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES    TO :"inv_user";
ALTER  DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO :"inv_user";
