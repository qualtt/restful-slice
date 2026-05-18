# Внешний балансировщик (VPS-C → два gateway)

Конфиги для отдельной машины с **Nginx** или **HAProxy**, которая принимает **80/443** и проксирует на два upstream. Для текущего стенда значения вынесены в env и рендерятся в конфиг (`155.212.221.216:80` и `5.181.109.6:80`).

| Путь | Назначение |
|------|------------|
| `vps-c/nginx/` | виртуальный хост + `upstream` |
| `vps-c/haproxy/` | альтернатива с активным `GET /health` |
| `gateway/` | примеры trusted proxy для Kong / Traefik |
| `load-balancer.env.example` | переменные для домена, upstream и IP балансировщика |
| `load-balancer.enc.env` | зашифрованный `dotenv` для реального деплоя через `sops` |
| `render-nginx-conf.sh` | рендер итогового `nginx`-конфига из env |
| `deploy.sh` | идемпотентный деплой `nginx`-конфига на VPS по SSH |
| `load-balancer-nginx-vps-c.md` | полный гайд |
| `WHAT-ELSE-YOU-NEED.ru.md` | чеклист: DNS, VPS-C, firewall, TLS |

Подставьте **IP балансировщика** вместо `REPLACE_WITH_VPS_C_IP` в `gateway/*` и в firewall на gateway-хостах.

Рендер конфига для `nginx`:

```bash
bash infra/load-balancer/render-nginx-conf.sh infra/load-balancer/load-balancer.env.example
```

Расшифровка отдельного env для балансировщика:

```bash
SOPS_AGE_KEY_FILE=infra/sops/keys.txt \
sops --decrypt --input-type dotenv --output-type dotenv \
  infra/load-balancer/load-balancer.enc.env > /tmp/load-balancer.env
```

Ручной деплой тем же env:

```bash
bash infra/load-balancer/deploy.sh /tmp/load-balancer.env
```

Для GitHub Actions self-hosted runner не нужен: workflow [load-balancer-deploy.yml](/workspaces/restful-slice/.github/workflows/load-balancer-deploy.yml) работает на `ubuntu-latest` и ходит на VPS по SSH. Нужны secrets:

- `SOPS_AGE_KEY`
- `LB_SSH_PRIVATE_KEY` или `LB_SSH_PASSWORD`
