#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" != "" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$1"
  set +a
fi

: "${LB_DOMAIN:?LB_DOMAIN is required}"
: "${LB_UPSTREAM_1:?LB_UPSTREAM_1 is required}"
: "${LB_UPSTREAM_2:?LB_UPSTREAM_2 is required}"

LB_DOMAIN_ALIASES="${LB_DOMAIN_ALIASES:-www.${LB_DOMAIN}}"
LB_LETSENCRYPT_LIVE_DIR="${LB_LETSENCRYPT_LIVE_DIR:-/etc/letsencrypt/live/${LB_DOMAIN}}"

if [ -n "${LB_DOMAIN_ALIASES}" ]; then
  server_names="${LB_DOMAIN} ${LB_DOMAIN_ALIASES}"
else
  server_names="${LB_DOMAIN}"
fi

cat <<EOF
upstream gateway_backends {
    least_conn;
    server ${LB_UPSTREAM_1} max_fails=3 fail_timeout=30s;
    server ${LB_UPSTREAM_2} max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name ${server_names};

    location ^~ /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${server_names};

    ssl_certificate ${LB_LETSENCRYPT_LIVE_DIR}/fullchain.pem;
    ssl_certificate_key ${LB_LETSENCRYPT_LIVE_DIR}/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_http_version 1.1;
        proxy_set_header Connection "";

        proxy_set_header Host              \$host;
        proxy_set_header X-Real-IP         \$remote_addr;
        proxy_set_header X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host  \$host;
        proxy_set_header X-Forwarded-Port  \$server_port;

        proxy_next_upstream error timeout http_502 http_503 http_504;
        proxy_next_upstream_tries 3;

        proxy_pass http://gateway_backends;
    }
}
EOF
