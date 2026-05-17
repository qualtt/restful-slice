import * as Sentry from "@sentry/browser";
import { syncTelemetryBatch, type TelemetryEvent } from "./api";

const FLUSH_INTERVAL_MS = 15_000;
const FLUSH_SIZE = 15;
const STORAGE_KEY = "rs_telemetry_queue_v1";
const MAX_QUEUE_SIZE = 600;
const CONSENT_VERSION = "2026-05";

function randomId(): string {
  const c = typeof globalThis.crypto !== "undefined" ? globalThis.crypto : undefined;
  if (!c?.getRandomValues) {
    return `${Date.now()}_${Math.random().toString(16).slice(2)}`;
  }

  try {
    if (typeof c.randomUUID === "function") {
      return c.randomUUID();
    }
  } catch {
    // В небезопасном контексте (голый HTTP по IP/домену без TLS) Chromium часто режет randomUUID —
    // см. ниже ручную сборку v4 через getRandomValues (она на HTTP доступна).
  }

  const bytes = new Uint8Array(16);
  c.getRandomValues(bytes);
  bytes[6] = (bytes[6]! & 0x0f) | 0x40;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;

  let hex = "";
  for (const b of bytes) {
    hex += b.toString(16).padStart(2, "0");
  }
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function getSessionId(): string {
  const key = "rs_session_id_v1";
  const existing = sessionStorage.getItem(key);
  if (existing) {
    return existing;
  }

  const created = randomId();
  sessionStorage.setItem(key, created);
  return created;
}

class Telemetry {
  private queue: TelemetryEvent[] = [];
  private consent = false;
  private timer?: number;
  private inFlight = false;
  private startedAt = Date.now();
  private routeEnterAt = Date.now();
  private currentRoute = "/";
  private sessionId = getSessionId();

  setConsent(value: boolean): void {
    this.consent = value;
    if (value) {
      this.restoreQueue();
      this.start();
      this.track("consent.granted", { at: new Date().toISOString() });
      this.captureDeviceContext();
      this.bindLifecycleSignals();
      void this.flush();
      return;
    }

    this.stop();
  }

  initSentry(): void {
    const dsn = import.meta.env.VITE_SENTRY_DSN;
    if (!dsn) {
      return;
    }

    Sentry.init({
      dsn,
      tracesSampleRate: 0.2
    });
  }

  track(name: string, data: Record<string, unknown> = {}): void {
    if (!this.consent) {
      return;
    }

    this.pushEvent({
      id: randomId(),
      name,
      ts: new Date().toISOString(),
      sessionId: this.sessionId,
      route: this.currentRoute,
      consentVersion: CONSENT_VERSION,
      context: {
        appVersion: import.meta.env.VITE_APP_VERSION ?? "dev",
        environment: import.meta.env.MODE,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        language: navigator.language
      },
      data
    });

    if (this.queue.length >= FLUSH_SIZE) {
      void this.flush();
    }
  }

  trackError(error: unknown, extra: Record<string, unknown> = {}): void {
    const message = error instanceof Error ? error.message : "unknown_error";
    this.track("client.error", { message, ...extra });
    Sentry.captureException(error, { extra });
  }

  trackRouteEnter(pathname: string): void {
    if (!this.consent) {
      return;
    }

    const now = Date.now();
    if (this.currentRoute) {
      const dwellMs = now - this.routeEnterAt;
      this.track("ux.route_dwell", { route: this.currentRoute, dwellMs });
    }

    this.currentRoute = pathname;
    this.routeEnterAt = now;
    this.track("ux.route_enter", { route: pathname });
  }

  async flush(): Promise<void> {
    if (this.inFlight || !this.consent || this.queue.length === 0) {
      return;
    }

    this.inFlight = true;
    const chunk = this.queue.slice(0, FLUSH_SIZE);
    try {
      await syncTelemetryBatch(chunk);
      this.queue = this.queue.slice(chunk.length);
      this.persistQueue();
    } catch (error) {
      this.track("telemetry.flush_failed", { phase: "flush" });
      this.persistQueue();
      if (import.meta.env.DEV) {
        console.warn("[telemetry] flush failed", error);
      }
    } finally {
      this.inFlight = false;
    }
  }

  private start(): void {
    if (this.timer) {
      return;
    }

    this.timer = window.setInterval(() => {
      void this.flush();
    }, FLUSH_INTERVAL_MS);
  }

  private stop(): void {
    if (this.timer) {
      window.clearInterval(this.timer);
      this.timer = undefined;
    }
  }

  private captureDeviceContext(): void {
    this.track("device.context", {
      userAgent: navigator.userAgent,
      language: navigator.language,
      screen: `${window.screen.width}x${window.screen.height}`,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      platform: navigator.platform,
      hardwareConcurrency: navigator.hardwareConcurrency,
      deviceMemory: (navigator as Navigator & { deviceMemory?: number }).deviceMemory
    });

    this.track("session.started", {
      startedAt: new Date(this.startedAt).toISOString(),
      referrer: document.referrer || "direct",
      online: navigator.onLine
    });
  }

  private bindLifecycleSignals(): void {
    window.addEventListener("online", () => {
      this.track("device.network_online");
      void this.flush();
    });
    window.addEventListener("offline", () => this.track("device.network_offline"));
    document.addEventListener("visibilitychange", () => {
      this.track("ux.visibility_changed", { state: document.visibilityState });
    });
    window.addEventListener("beforeunload", () => {
      this.track("session.ended", { durationMs: Date.now() - this.startedAt });
      this.persistQueue();
      void this.flush();
    });
  }

  bindClickTracking(): void {
    document.addEventListener("click", (event) => {
      if (!this.consent) {
        return;
      }

      const target = event.target as HTMLElement | null;
      if (!target) {
        return;
      }

      const el = target.closest<HTMLElement>("button,a,[data-telemetry]");
      if (!el) {
        return;
      }

      const label = (
        el.getAttribute("data-telemetry-label") ??
        el.getAttribute("aria-label") ??
        el.textContent ??
        "unknown"
      )
        .trim()
        .slice(0, 120);

      this.track("ux.click", {
        tag: el.tagName.toLowerCase(),
        id: el.id || undefined,
        className: el.className || undefined,
        label
      });
    });
  }

  trackPerformanceSnapshot(): void {
    if (!this.consent) {
      return;
    }

    const nav = performance.getEntriesByType("navigation")[0] as
      | PerformanceNavigationTiming
      | undefined;
    if (nav) {
      this.track("perf.navigation", {
        domComplete: Math.round(nav.domComplete),
        domInteractive: Math.round(nav.domInteractive),
        responseEnd: Math.round(nav.responseEnd),
        loadEventEnd: Math.round(nav.loadEventEnd),
        transferSize: nav.transferSize
      });
    }

    const memory = (performance as Performance & {
      memory?: { usedJSHeapSize: number; jsHeapSizeLimit: number };
    }).memory;
    if (memory) {
      this.track("perf.memory", {
        usedJSHeapSize: memory.usedJSHeapSize,
        jsHeapSizeLimit: memory.jsHeapSizeLimit
      });
    }
  }

  private pushEvent(event: TelemetryEvent): void {
    this.queue.push(event);
    if (this.queue.length > MAX_QUEUE_SIZE) {
      this.queue.splice(0, this.queue.length - MAX_QUEUE_SIZE);
    }
    this.persistQueue();
  }

  private persistQueue(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.queue));
    } catch (error) {
      if (import.meta.env.DEV) {
        console.warn("[telemetry] queue persist failed", error);
      }
    }
  }

  private restoreQueue(): void {
    if (this.queue.length > 0) {
      return;
    }

    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return;
      }
      const parsed = JSON.parse(raw) as TelemetryEvent[];
      if (Array.isArray(parsed)) {
        this.queue = parsed.slice(-MAX_QUEUE_SIZE);
      }
    } catch {
      this.queue = [];
    }
  }
}

export const telemetry = new Telemetry();
