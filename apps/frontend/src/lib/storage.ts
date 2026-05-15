const CONSENT_KEY = "rs_consent_v1";

export interface ConsentState {
  accepted: boolean;
  acceptedAt: string;
  version: string;
}

export function getConsent(): ConsentState | null {
  const value = localStorage.getItem(CONSENT_KEY);
  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value) as ConsentState;
  } catch {
    return null;
  }
}

export function saveConsent(consent: ConsentState): void {
  localStorage.setItem(CONSENT_KEY, JSON.stringify(consent));
}
