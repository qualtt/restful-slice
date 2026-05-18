#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${1:-$ROOT/infra/load-balancer/load-balancer.env}"

if [ ! -f "$ENV_FILE" ]; then
    echo "deploy.sh: env file not found: $ENV_FILE" >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

: "${LB_DOMAIN:?LB_DOMAIN is required}"
: "${LB_BALANCER_PUBLIC_IP:?LB_BALANCER_PUBLIC_IP is required}"

DEPLOY_HOST="${LB_DEPLOY_HOST:-$LB_BALANCER_PUBLIC_IP}"
DEPLOY_USER="${LB_DEPLOY_USER:-root}"
DEPLOY_PORT="${LB_DEPLOY_PORT:-22}"
SITE_NAME="${LB_NGINX_SITE_NAME:-${LB_DOMAIN}.conf}"
SSH_BIN="${LB_SSH_BIN:-ssh}"
SCP_BIN="${LB_SCP_BIN:-scp}"

rendered_conf="$(mktemp)"
trap 'rm -f "$rendered_conf"' EXIT

bash "$ROOT/infra/load-balancer/render-nginx-conf.sh" "$ENV_FILE" > "$rendered_conf"

"$SCP_BIN" -P "$DEPLOY_PORT" "$rendered_conf" "$DEPLOY_USER@$DEPLOY_HOST:/tmp/$SITE_NAME"

"$SSH_BIN" -p "$DEPLOY_PORT" "$DEPLOY_USER@$DEPLOY_HOST" "bash -s" -- "$SITE_NAME" "$DEPLOY_USER" <<'EOF'
set -euo pipefail

site_name="$1"
deploy_user="$2"

if [ "$deploy_user" = "root" ]; then
    sudo_cmd=""
else
    sudo_cmd="sudo"
fi

$sudo_cmd apt-get update
$sudo_cmd apt-get install -y nginx
$sudo_cmd mkdir -p /var/www/certbot /etc/nginx/sites-available /etc/nginx/sites-enabled
$sudo_cmd mv "/tmp/$site_name" "/etc/nginx/sites-available/$site_name"
$sudo_cmd chmod 644 "/etc/nginx/sites-available/$site_name"
$sudo_cmd ln -sfn "/etc/nginx/sites-available/$site_name" "/etc/nginx/sites-enabled/$site_name"
$sudo_cmd rm -f /etc/nginx/sites-enabled/default
$sudo_cmd nginx -t
$sudo_cmd systemctl enable --now nginx
$sudo_cmd systemctl reload nginx
EOF
