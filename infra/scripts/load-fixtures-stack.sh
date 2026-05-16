#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  . ./.env
  set +a
fi

FIXTURES_DIR="${FIXTURES_DIR:-$ROOT_DIR/tests/postman/fixtures}"
PROFILE_FIXTURES_DIR="$FIXTURES_DIR/profiles"
STACK_NAME="${STACK_NAME:-restful-slice}"
STACK_NETWORK="${STACK_NETWORK:-${STACK_NAME}_backend_net}"
MINIO_SERVICE_NAME="${MINIO_SERVICE_NAME:-${STACK_NAME}_minio}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minio_secret_123}"
MINIO_BUCKET_NAME="${MINIO_BUCKET_NAME:-3d-models}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-minio:9000}"

if [[ "$MINIO_ENDPOINT" == http://* || "$MINIO_ENDPOINT" == https://* ]]; then
  MINIO_URL="$MINIO_ENDPOINT"
else
  MINIO_URL="http://$MINIO_ENDPOINT"
fi

if [[ ! -d "$PROFILE_FIXTURES_DIR" ]]; then
  echo "Profile fixtures directory not found: $PROFILE_FIXTURES_DIR" >&2
  exit 1
fi

SWARM_STATE="$(docker info --format '{{.Swarm.LocalNodeState}}')"
if [[ "$SWARM_STATE" != "active" ]]; then
  echo "Docker Swarm is not active on this host." >&2
  exit 1
fi

SWARM_MANAGER="$(docker info --format '{{.Swarm.ControlAvailable}}')"
if [[ "$SWARM_MANAGER" != "true" ]]; then
  echo "This script must run on a Swarm manager because it creates a temporary service." >&2
  exit 1
fi

if ! docker service inspect "$MINIO_SERVICE_NAME" >/dev/null 2>&1; then
  echo "MinIO swarm service not found: $MINIO_SERVICE_NAME" >&2
  echo "Deploy the stack first: docker stack deploy -c docker-stack.yml $STACK_NAME" >&2
  exit 1
fi

if ! docker network inspect "$STACK_NETWORK" >/dev/null 2>&1; then
  echo "Swarm network not found: $STACK_NETWORK" >&2
  echo "Deploy the stack first: docker stack deploy -c docker-stack.yml $STACK_NAME" >&2
  exit 1
fi

CURRENT_NODE_HOSTNAME="$(docker info --format '{{.Name}}')"
TEMP_SERVICE_NAME="${STACK_NAME}_fixtures_loader_$(date +%s)_$$"

cleanup() {
  if docker service inspect "$TEMP_SERVICE_NAME" >/dev/null 2>&1; then
    docker service rm "$TEMP_SERVICE_NAME" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

docker service create \
  --quiet \
  --name "$TEMP_SERVICE_NAME" \
  --network "$STACK_NETWORK" \
  --constraint "node.hostname == $CURRENT_NODE_HOSTNAME" \
  --restart-condition none \
  --mount "type=bind,src=$PROFILE_FIXTURES_DIR,dst=/fixtures/profiles,ro" \
  --env "MINIO_ROOT_USER=$MINIO_ROOT_USER" \
  --env "MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD" \
  --env "MINIO_BUCKET_NAME=$MINIO_BUCKET_NAME" \
  --env "MINIO_URL=$MINIO_URL" \
  --entrypoint sh \
  minio/mc -c '
    set -eu
    mc alias set local "$MINIO_URL" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null
    attempts=0
    until mc ls local >/dev/null 2>&1; do
      attempts=$((attempts + 1))
      if [ "$attempts" -ge 60 ]; then
        echo "Timed out waiting for MinIO at $MINIO_URL" >&2
        exit 1
      fi
      sleep 2
    done
    mc mb -p "local/$MINIO_BUCKET_NAME" 2>/dev/null || true
    mc mirror --overwrite /fixtures/profiles "local/$MINIO_BUCKET_NAME/profiles"
  ' >/dev/null

deadline=$((SECONDS + 180))
while (( SECONDS < deadline )); do
  current_state="$(docker service ps --no-trunc --format '{{.CurrentState}}' "$TEMP_SERVICE_NAME" | head -n 1 || true)"
  state="${current_state%% *}"

  case "$state" in
    Complete)
      echo "Uploaded fixture profiles from $PROFILE_FIXTURES_DIR to s3://$MINIO_BUCKET_NAME/profiles/ via stack $STACK_NAME"
      exit 0
      ;;
    Failed|Rejected|Remove)
      docker service logs "$TEMP_SERVICE_NAME" 2>/dev/null || true
      echo "Fixture loader service failed: ${current_state:-unknown state}" >&2
      exit 1
      ;;
    New|Pending|Assigned|Accepted|Preparing|Ready|Starting|Running|"")
      sleep 2
      ;;
    *)
      if [[ "$current_state" == Complete* ]]; then
        echo "Uploaded fixture profiles from $PROFILE_FIXTURES_DIR to s3://$MINIO_BUCKET_NAME/profiles/ via stack $STACK_NAME"
        exit 0
      fi
      if [[ "$current_state" == Failed* || "$current_state" == Rejected* ]]; then
        docker service logs "$TEMP_SERVICE_NAME" 2>/dev/null || true
        echo "Fixture loader service failed: $current_state" >&2
        exit 1
      fi
      sleep 2
      ;;
  esac
done

docker service logs "$TEMP_SERVICE_NAME" 2>/dev/null || true
echo "Timed out waiting for temporary service $TEMP_SERVICE_NAME to finish." >&2
exit 1
