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
DOCKER_COMMAND_TIMEOUT_SECONDS="${DOCKER_COMMAND_TIMEOUT_SECONDS:-20}"
SERVICE_CREATE_TIMEOUT_SECONDS="${SERVICE_CREATE_TIMEOUT_SECONDS:-30}"
SERVICE_WAIT_TIMEOUT_SECONDS="${SERVICE_WAIT_TIMEOUT_SECONDS:-180}"
SERVICE_DIAGNOSTICS_TIMEOUT_SECONDS="${SERVICE_DIAGNOSTICS_TIMEOUT_SECONDS:-15}"
STATUS_LOG_INTERVAL_SECONDS="${STATUS_LOG_INTERVAL_SECONDS:-15}"

if [[ "$MINIO_ENDPOINT" == http://* || "$MINIO_ENDPOINT" == https://* ]]; then
  MINIO_URL="$MINIO_ENDPOINT"
else
  MINIO_URL="http://$MINIO_ENDPOINT"
fi

run_with_timeout() {
  local seconds="$1"
  shift
  local status

  set +e
  if command -v timeout >/dev/null 2>&1; then
    timeout --foreground "${seconds}s" "$@"
  else
    "$@"
  fi
  status=$?
  set -e

  if [[ "$status" -eq 124 ]]; then
    echo "Timed out after ${seconds}s: $*" >&2
  fi

  return "$status"
}

docker_cmd() {
  run_with_timeout "$DOCKER_COMMAND_TIMEOUT_SECONDS" docker "$@"
}

if [[ ! -d "$PROFILE_FIXTURES_DIR" ]]; then
  echo "Profile fixtures directory not found: $PROFILE_FIXTURES_DIR" >&2
  exit 1
fi

SWARM_STATE="$(docker_cmd info --format '{{.Swarm.LocalNodeState}}')"
if [[ "$SWARM_STATE" != "active" ]]; then
  echo "Docker Swarm is not active on this host." >&2
  exit 1
fi

SWARM_MANAGER="$(docker_cmd info --format '{{.Swarm.ControlAvailable}}')"
if [[ "$SWARM_MANAGER" != "true" ]]; then
  echo "This script must run on a Swarm manager because it creates a temporary service." >&2
  exit 1
fi

if ! docker_cmd service inspect "$MINIO_SERVICE_NAME" >/dev/null 2>&1; then
  echo "MinIO swarm service not found: $MINIO_SERVICE_NAME" >&2
  echo "Deploy the stack first: docker stack deploy -c docker-stack.yml $STACK_NAME" >&2
  exit 1
fi

if ! docker_cmd network inspect "$STACK_NETWORK" >/dev/null 2>&1; then
  echo "Swarm network not found: $STACK_NETWORK" >&2
  echo "Deploy the stack first: docker stack deploy -c docker-stack.yml $STACK_NAME" >&2
  exit 1
fi

CURRENT_NODE_HOSTNAME="$(docker_cmd info --format '{{.Name}}')"
TEMP_SERVICE_NAME="${STACK_NAME}_fixtures_loader_$(date +%s)_$$"

print_service_diagnostics() {
  echo "Fixture loader diagnostics for $TEMP_SERVICE_NAME:" >&2
  run_with_timeout "$SERVICE_DIAGNOSTICS_TIMEOUT_SECONDS" docker service ps --no-trunc "$TEMP_SERVICE_NAME" 1>&2 || true
  run_with_timeout "$SERVICE_DIAGNOSTICS_TIMEOUT_SECONDS" docker service logs "$TEMP_SERVICE_NAME" 1>&2 || true
}

cleanup() {
  if docker_cmd service inspect "$TEMP_SERVICE_NAME" >/dev/null 2>&1; then
    run_with_timeout "$SERVICE_DIAGNOSTICS_TIMEOUT_SECONDS" docker service rm "$TEMP_SERVICE_NAME" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

if ! run_with_timeout "$SERVICE_CREATE_TIMEOUT_SECONDS" \
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
    ' >/dev/null; then
  echo "Failed to create temporary fixture loader service $TEMP_SERVICE_NAME." >&2
  exit 1
fi

deadline=$((SECONDS + SERVICE_WAIT_TIMEOUT_SECONDS))
last_state=""
last_status_log_at=0

echo "Waiting up to ${SERVICE_WAIT_TIMEOUT_SECONDS}s for temporary service $TEMP_SERVICE_NAME to upload fixtures..."
while (( SECONDS < deadline )); do
  current_state="$(
    docker_cmd service ps --no-trunc --format '{{.CurrentState}}' "$TEMP_SERVICE_NAME" | head -n 1
  )" || {
    print_service_diagnostics
    echo "Unable to inspect fixture loader service state." >&2
    exit 1
  }
  state="${current_state%% *}"

  if [[ "$current_state" != "$last_state" || $((SECONDS - last_status_log_at)) -ge STATUS_LOG_INTERVAL_SECONDS ]]; then
    echo "Fixture loader state: ${current_state:-unknown}" >&2
    last_state="$current_state"
    last_status_log_at="$SECONDS"
  fi

  case "$state" in
    Complete)
      echo "Uploaded fixture profiles from $PROFILE_FIXTURES_DIR to s3://$MINIO_BUCKET_NAME/profiles/ via stack $STACK_NAME"
      exit 0
      ;;
    Failed|Rejected|Remove)
      print_service_diagnostics
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
        print_service_diagnostics
        echo "Fixture loader service failed: $current_state" >&2
        exit 1
      fi
      sleep 2
      ;;
  esac
done

print_service_diagnostics
echo "Timed out waiting for temporary service $TEMP_SERVICE_NAME to finish." >&2
exit 1
