# Внешний балансировщик (VPS-C → два gateway)

Конфиги для отдельной машины с **Nginx** или **HAProxy**, которая принимает **80/443** и проксирует на два upstream. Для текущего стенда значения вынесены в env и рендерятся в конфиг (`155.212.221.216:80` и `5.181.109.6:80`).

| Путь | Назначение |
|------|------------|
| `vps-c/nginx/` | виртуальный хост + `upstream` |
| `vps-c/haproxy/` | альтернатива с активным `GET /health` |
| `gateway/` | примеры trusted proxy для Kong / Traefik |
| `load-balancer.env.example` | переменные для домена, upstream и IP балансировщика |
| `render-nginx-conf.sh` | рендер итогового `nginx`-конфига из env |
| `load-balancer-nginx-vps-c.md` | полный гайд |
| `WHAT-ELSE-YOU-NEED.ru.md` | чеклист: DNS, VPS-C, firewall, TLS |

Подставьте **IP балансировщика** вместо `REPLACE_WITH_VPS_C_IP` в `gateway/*` и в firewall на gateway-хостах.

Рендер конфига для `nginx`:

```bash
bash infra/load-balancer/render-nginx-conf.sh infra/load-balancer/load-balancer.env.example
```
