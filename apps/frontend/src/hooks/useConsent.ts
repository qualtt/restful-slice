import { useMemo, useState } from "react";
import { getConsent, saveConsent, type ConsentState } from "../lib/storage";
import { telemetry } from "../lib/telemetry";

const CONSENT_VERSION = "2026-05";

export function useConsent() {
  const [consent, setConsent] = useState<ConsentState | null>(() => getConsent());

  const accepted = useMemo(
    () => Boolean(consent?.accepted && consent.version === CONSENT_VERSION),
    [consent]
  );

  function accept(): void {
    const next: ConsentState = {
      accepted: true,
      acceptedAt: new Date().toISOString(),
      version: CONSENT_VERSION
    };
    saveConsent(next);
    setConsent(next);
    telemetry.setConsent(true);
  }

  return { accepted, consent, accept };
}
