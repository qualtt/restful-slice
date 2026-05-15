import { OrderList } from "../components/dashboard/OrderList";
import { UploadOrderPanel } from "../components/dashboard/UploadOrderPanel";
import { Card } from "../components/common/Card";

export function DashboardPage() {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[380px_1fr]">
      <UploadOrderPanel />
      <OrderList />
      <Card className="lg:col-span-2" title="Slicing insights">
        <p className="text-sm text-black">
          Upload funnel, order statuses, and client diagnostics are tracked only after explicit
          user consent.
        </p>
      </Card>
    </div>
  );
}
