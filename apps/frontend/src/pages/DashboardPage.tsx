import { OrderList } from "../components/dashboard/OrderList";
import { IdentityPanel } from "../components/dashboard/IdentityPanel";
import { StatusCanvas } from "../components/dashboard/StatusCanvas";
import { UploadOrderPanel } from "../components/dashboard/UploadOrderPanel";
import { Card } from "../components/common/Card";

export function DashboardPage() {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[340px_1fr]">
      <IdentityPanel />
      <UploadOrderPanel />
      <OrderList />
      <StatusCanvas />
      <Card className="lg:col-span-2" title="Slicing insights">
        <p className="text-sm text-black">
          Upload funnel, order statuses, and client diagnostics are tracked only after explicit
          consent and are scoped to the active API-key identity.
        </p>
      </Card>
    </div>
  );
}
