# Внешний балансировщик (VPS-C → два gateway)

Конфиги для отдельной машины с **Nginx** или **HAProxy**, которая принимает **80/443** и проксирует на два upstream (сейчас в примерах: `155.212.221.216` и `5.181.109.6`, порт **8080**).

| Путь | Назначение |
|------|------------|
| `vps-c/nginx/` | виртуальный хост + `upstream` |
| `vps-c/haproxy/` | альтернатива с активным `GET /health` |
| `gateway/` | примеры trusted proxy для Kong / Traefik |
| `load-balancer-nginx-vps-c.md` | полный гайд |
| `WHAT-ELSE-YOU-NEED.ru.md` | чеклист: DNS, VPS-C, firewall, TLS |

Подставьте **IP балансировщика** вместо `REPLACE_WITH_VPS_C_IP` в `gateway/*` и в firewall на gateway-хостах.
