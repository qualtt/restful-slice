import type { ApiIdentity } from "../../types/api";
import { Card } from "../common/Card";

const identity: ApiIdentity = {
  apiKeyLabel: "OPS-RED-07",
  owner: "Night shift operator",
  role: "slicing control",
  fingerprint: "api_key_id: 4f21c0d8"
};

export function IdentityPanel() {
  return (
    <Card title="Operator identity" className="space-y-3">
      <p className="text-sm text-black">
        API-key identity is the active session token for dashboard actions and telemetry.
      </p>
      <div className="grid gap-2 text-xs">
        <div className="identity-row">
          <span>Key label</span>
          <strong>{identity.apiKeyLabel}</strong>
        </div>
        <div className="identity-row">
          <span>Owner</span>
          <strong>{identity.owner}</strong>
        </div>
        <div className="identity-row">
          <span>Role</span>
          <strong>{identity.role}</strong>
        </div>
        <div className="identity-row">
          <span>Fingerprint</span>
          <strong>{identity.fingerprint}</strong>
        </div>
      </div>
    </Card>
  );
}
