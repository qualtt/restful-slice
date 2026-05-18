# restful-slice frontend

## Architecture

- `src/lib/api.ts`: typed REST client for `order-service`, `inventory-service`, telemetry sync.
- `src/lib/telemetry.ts`: consent-gated event queue, batching, periodic flush, Sentry bridge.
- `src/components/dashboard/*`: dashboard widgets (upload, operator identity, canvas monitor + order stream).
- `src/components/consent/*`: CMP modal shown on first visit.
- `src/pages/*`: route-level screens.

## Data collection model

Collection starts only after explicit consent in `ConsentModal` and is scoped to the current API-key identity.

Tracked events:

- Device context (`userAgent`, screen, language, timezone)
- Session and route dwell metrics
- Upload funnel events (`accepted`, `started`, `file.success`, `order.created`, rejections)
- API UX metrics (`inventory.profiles_loaded`, `orders.list_loaded`, failure events)
- Generic UI clickstream (`ux.click`) for buttons/links/telemetry-marked controls
- Performance snapshots (navigation timing + JS heap if available)
- Connectivity/lifecycle (`online/offline`, visibility changes, session end)
- Client errors and unhandled promise rejections

Events are batched and sent every 15s or when queue reaches 15 events.
Queue is persisted to localStorage and restored after reload (offline-safe), capped at 600 events.

## Environment variables

- `VITE_API_BASE_URL` - optional API base URL (default same origin).
- `VITE_API_KEY` - optional API key sent as `X-API-Key` on frontend requests.
- `VITE_ANALYTICS_ENDPOINT` - telemetry endpoint (default `/api/telemetry/events`).
- `VITE_SENTRY_DSN` - optional Sentry DSN.
- `VITE_APP_VERSION` - optional app version label attached to each event.

## Run

```bash
npm install
npm run dev
```
