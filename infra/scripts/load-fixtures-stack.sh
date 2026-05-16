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
MINIO_SERVICE_NAME="${MINIO_SERVICE_NAME:-${STACK_NAME}_minio}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minio_secret_123}"
MINIO_BUCKET_NAME="${MINIO_BUCKET_NAME:-3d-models}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-minio:9000}"
DOCKER_COMMAND_TIMEOUT_SECONDS="${DOCKER_COMMAND_TIMEOUT_SECONDS:-20}"
MINIO_CONTAINER_WAIT_TIMEOUT_SECONDS="${MINIO_CONTAINER_WAIT_TIMEOUT_SECONDS:-120}"
MINIO_READY_WAIT_TIMEOUT_SECONDS="${MINIO_READY_WAIT_TIMEOUT_SECONDS:-120}"
HELPER_RUN_TIMEOUT_SECONDS="${HELPER_RUN_TIMEOUT_SECONDS:-180}"
IMAGE_PULL_TIMEOUT_SECONDS="${IMAGE_PULL_TIMEOUT_SECONDS:-120}"
SERVICE_DIAGNOSTICS_TIMEOUT_SECONDS="${SERVICE_DIAGNOSTICS_TIMEOUT_SECONDS:-15}"
STATUS_LOG_INTERVAL_SECONDS="${STATUS_LOG_INTERVAL_SECONDS:-15}"
MC_IMAGE="${MC_IMAGE:-minio/mc}"

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

helper_minio_url() {
  if [[ "$MINIO_URL" =~ ^(https?)://[^/:]+(:[0-9]+)?(/.*)?$ ]]; then
    printf '%s://127.0.0.1%s%s\n' \
      "${BASH_REMATCH[1]}" \
      "${BASH_REMATCH[2]}" \
      "${BASH_REMATCH[3]}"
  else
    printf 'http://127.0.0.1:9000\n'
  fi
}

get_minio_container_id() {
  docker_cmd ps \
    --filter "label=com.docker.swarm.service.name=$MINIO_SERVICE_NAME" \
    --filter "status=running" \
    --format '{{.ID}}' \
    | head -n 1
}

print_minio_diagnostics() {
  echo "MinIO service diagnostics for $MINIO_SERVICE_NAME:" >&2
  run_with_timeout "$SERVICE_DIAGNOSTICS_TIMEOUT_SECONDS" docker service ps --no-trunc "$MINIO_SERVICE_NAME" 1>&2 || true
  run_with_timeout "$SERVICE_DIAGNOSTICS_TIMEOUT_SECONDS" docker ps \
    --filter "label=com.docker.swarm.service.name=$MINIO_SERVICE_NAME" \
    --format 'table {{.ID}}\t{{.Status}}\t{{.Names}}' 1>&2 || true
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
  echo "This script must run on a Swarm manager because it inspects Swarm services directly." >&2
  exit 1
fi

if ! docker_cmd service inspect "$MINIO_SERVICE_NAME" >/dev/null 2>&1; then
  echo "MinIO swarm service not found: $MINIO_SERVICE_NAME" >&2
  echo "Deploy the stack first: docker stack deploy -c docker-stack.yml $STACK_NAME" >&2
  exit 1
fi

deadline=$((SECONDS + MINIO_CONTAINER_WAIT_TIMEOUT_SECONDS))
MINIO_CONTAINER_ID=""
last_status_log_at=0

echo "Waiting up to ${MINIO_CONTAINER_WAIT_TIMEOUT_SECONDS}s for a local MinIO task container from service $MINIO_SERVICE_NAME..."
while (( SECONDS < deadline )); do
  MINIO_CONTAINER_ID="$(get_minio_container_id)" || {
    print_minio_diagnostics
    echo "Unable to inspect MinIO task containers." >&2
    exit 1
  }

  if [[ -n "$MINIO_CONTAINER_ID" ]]; then
    break
  fi

  if (( SECONDS - last_status_log_at >= STATUS_LOG_INTERVAL_SECONDS )); then
    echo "MinIO task container is not running yet." >&2
    last_status_log_at="$SECONDS"
  fi

  sleep 2
done

if [[ -z "$MINIO_CONTAINER_ID" ]]; then
  print_minio_diagnostics
  echo "Timed out waiting for a running MinIO task container." >&2
  exit 1
fi

echo "Using local MinIO container $MINIO_CONTAINER_ID."

if ! docker_cmd image inspect "$MC_IMAGE" >/dev/null 2>&1; then
  echo "Pulling helper image $MC_IMAGE..." >&2
  if ! run_with_timeout "$IMAGE_PULL_TIMEOUT_SECONDS" docker pull "$MC_IMAGE"; then
    echo "Failed to pull helper image $MC_IMAGE." >&2
    exit 1
  fi
fi

HELPER_MINIO_URL="$(helper_minio_url)"
echo "Uploading fixtures via helper container in MinIO network namespace (${HELPER_MINIO_URL})."

if ! run_with_timeout "$HELPER_RUN_TIMEOUT_SECONDS" \
  docker run --rm \
    --pull never \
    --network "container:$MINIO_CONTAINER_ID" \
    --mount "type=bind,src=$PROFILE_FIXTURES_DIR,dst=/fixtures/profiles,ro" \
    --env "MINIO_ROOT_USER=$MINIO_ROOT_USER" \
    --env "MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD" \
    --env "MINIO_BUCKET_NAME=$MINIO_BUCKET_NAME" \
    --env "MINIO_URL=$HELPER_MINIO_URL" \
    --env "MINIO_READY_WAIT_TIMEOUT_SECONDS=$MINIO_READY_WAIT_TIMEOUT_SECONDS" \
    --entrypoint sh \
    "$MC_IMAGE" -c '
      set -eu
      attempts=0
      max_attempts=$((MINIO_READY_WAIT_TIMEOUT_SECONDS / 2))
      if [ "$max_attempts" -lt 1 ]; then
        max_attempts=1
      fi

      mc alias set local "$MINIO_URL" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null
      until mc ls local >/dev/null 2>&1; do
        attempts=$((attempts + 1))
        if [ "$attempts" -ge "$max_attempts" ]; then
          echo "Timed out waiting for MinIO at $MINIO_URL" >&2
          exit 1
        fi
        sleep 2
      done

      mc mb -p "local/$MINIO_BUCKET_NAME" 2>/dev/null || true
      mc mirror --overwrite /fixtures/profiles "local/$MINIO_BUCKET_NAME/profiles"
    '; then
  print_minio_diagnostics
  echo "Failed to upload fixtures into MinIO." >&2
  exit 1
fi

echo "Uploaded fixture profiles from $PROFILE_FIXTURES_DIR to s3://$MINIO_BUCKET_NAME/profiles/ via stack $STACK_NAME"
