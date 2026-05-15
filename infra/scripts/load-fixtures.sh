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
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minio_secret_123}"
MINIO_BUCKET_NAME="${MINIO_BUCKET_NAME:-3d-models}"

if [[ ! -d "$PROFILE_FIXTURES_DIR" ]]; then
  echo "Profile fixtures directory not found: $PROFILE_FIXTURES_DIR" >&2
  exit 1
fi

MINIO_CONTAINER_ID="$(docker compose ps -q minio)"
if [[ -z "$MINIO_CONTAINER_ID" ]]; then
  echo "minio container is not running. Start the stack first: docker compose up --build -d" >&2
  exit 1
fi

BACKEND_NETWORK="$(
  docker inspect "$MINIO_CONTAINER_ID" \
    --format '{{range $name, $_ := .NetworkSettings.Networks}}{{println $name}}{{end}}' \
    | head -n 1 \
    | tr -d '[:space:]'
)"

if [[ -z "$BACKEND_NETWORK" ]]; then
  echo "Unable to detect the Docker network used by MinIO." >&2
  exit 1
fi

docker run --rm \
  --network "$BACKEND_NETWORK" \
  -v "$PROFILE_FIXTURES_DIR:/fixtures/profiles:ro" \
  --entrypoint sh \
  minio/mc -c "
    mc alias set local http://minio:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD >/dev/null
    mc mb -p local/$MINIO_BUCKET_NAME 2>/dev/null || true
    mc mirror --overwrite /fixtures/profiles local/$MINIO_BUCKET_NAME/profiles
  "

echo "Uploaded fixture profiles from $PROFILE_FIXTURES_DIR to s3://$MINIO_BUCKET_NAME/profiles/"
