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
export POSTGRES_SUPERUSER="${POSTGRES_SUPERUSER:-postgres}"
export POSTGRES_SUPERUSER_PASSWORD="${POSTGRES_SUPERUSER_PASSWORD:-${POSTGRES_PASSWORD:-}}"

# Имя Swarm config HAProxy версионируется — содержимое config в Swarm нельзя обновить.
export POSTGRES_HA_HAPROXY_CFG_VERSION="${POSTGRES_HA_HAPROXY_CFG_VERSION:-$(sha256sum "$ROOT/infra/patroni/haproxy.cfg" | cut -c1-12)}"

if [ -z "$POSTGRES_SUPERUSER_PASSWORD" ]; then
	echo "deploy-postgres-ha: задайте POSTGRES_SUPERUSER_PASSWORD или POSTGRES_PASSWORD в окружении / .env" >&2
	exit 1
fi

exec docker stack deploy --with-registry-auth -c infra/patroni/stack.yml postgres-ha
