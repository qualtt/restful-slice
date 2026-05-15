import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { ConsentModal } from "./components/consent/ConsentModal";
import { useConsent } from "./hooks/useConsent";
import { telemetry } from "./lib/telemetry";
import { DashboardPage } from "./pages/DashboardPage";

export default function App() {
  const { accepted, accept } = useConsent();
  const location = useLocation();

  useEffect(() => {
    telemetry.initSentry();
    telemetry.bindClickTracking();
  }, []);

  useEffect(() => {
    telemetry.setConsent(accepted);
  }, [accepted]);

  useEffect(() => {
    telemetry.trackRouteEnter(location.pathname);
  }, [location.pathname]);

  useEffect(() => {
    if (!accepted) {
      return;
    }

    telemetry.trackPerformanceSnapshot();
    const id = window.setInterval(() => {
      telemetry.trackPerformanceSnapshot();
    }, 60_000);
    return () => window.clearInterval(id);
  }, [accepted]);

  useEffect(() => {
    function onWindowError(event: ErrorEvent) {
      telemetry.trackError(event.error ?? event.message, { source: "window.onerror" });
    }

    function onUnhandledRejection(event: PromiseRejectionEvent) {
      telemetry.trackError(event.reason, { source: "window.unhandledrejection" });
    }

    window.addEventListener("error", onWindowError);
    window.addEventListener("unhandledrejection", onUnhandledRejection);
    return () => {
      window.removeEventListener("error", onWindowError);
      window.removeEventListener("unhandledrejection", onUnhandledRejection);
    };
  }, []);

  return (
    <AppShell>
      <ConsentModal open={!accepted} onAccept={accept} />
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
