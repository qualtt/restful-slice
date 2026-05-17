#!/usr/bin/env bash
# Деплоит postgres-ha так же, как CI: подхват .env, дефолт сети, суперпользователь Postgres.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then
	set -a
	# shellcheck disable=1091
	source ./.env
	set +a
fi

export RESTFUL_BACKEND_NET_NAME="${RESTFUL_BACKEND_NET_NAME:-restful-slice_backend_net}"
export POSTGRES_SUPERUSER="${POSTGRES_SUPERUSER:-${POSTGRES_USER:-}}"
export POSTGRES_SUPERUSER_PASSWORD="${POSTGRES_SUPERUSER_PASSWORD:-${POSTGRES_PASSWORD:-}}"

if [ -z "$POSTGRES_SUPERUSER_PASSWORD" ]; then
	echo "deploy-postgres-ha: задайте POSTGRES_SUPERUSER_PASSWORD или POSTGRES_PASSWORD в окружении / .env" >&2
	exit 1
fi

exec docker stack deploy --with-registry-auth -c infra/patroni/stack.yml postgres-ha
