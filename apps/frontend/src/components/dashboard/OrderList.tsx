import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { getOrders } from "../../lib/api";
import { formatAgo, formatSeconds } from "../../lib/format";
import { Card } from "../common/Card";
import { telemetry } from "../../lib/telemetry";

const statusClasses: Record<string, string> = {
  pending: "text-gray-600",
  slicing: "text-blue-600 font-bold",
  priced: "text-green-700 font-bold",
  failed: "text-red-600 font-bold",
  cancelled: "text-gray-500 line-through",
  confirmed: "text-blue-800 font-bold",
  printing: "text-orange-600 font-bold",
  completed: "text-green-800 font-bold"
};

export function OrderList() {
  const query = useQuery({
    queryKey: ["orders"],
    queryFn: getOrders,
    refetchInterval: 8_000
  });

  useEffect(() => {
    if (query.isSuccess) {
      telemetry.track("orders.list_loaded", {
        total: query.data.meta.total,
        page: query.data.meta.page,
        pageSize: query.data.meta.pageSize
      });
    }
  }, [query.isSuccess, query.data]);

  useEffect(() => {
    if (query.isError) {
      telemetry.track("orders.list_failed");
    }
  }, [query.isError]);

  return (
    <Card title="Orders" className="space-y-4">
      <div className="flex items-center justify-between border-b border-gray-400 pb-2">
        <span className="text-xs text-black">Auto refresh: 8s</span>
      </div>

      {query.isLoading && <p className="text-sm text-black">Loading orders...</p>}
      {query.isError && (
        <p className="text-sm text-red-700 font-bold">
          Unable to load orders. Check gateway/routes and service health.
        </p>
      )}

      <div className="space-y-3">
        {(query.data?.data ?? []).map((order) => (
          <article
            key={order.orderId}
            className="border-2 border-t-gray-800 border-l-gray-800 border-b-white border-r-white bg-white p-2 text-black"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-mono text-xs text-gray-600">ID: {order.orderId}</p>
                <p className="mt-1 text-sm font-bold">Profile #{order.profileId}</p>
              </div>
              <span
                className={`text-xs uppercase border border-gray-400 px-1 bg-gray-200 ${statusClasses[order.status] ?? statusClasses.pending}`}
              >
                [{order.status}]
              </span>
            </div>

            {order.slicingResult && (
              <div className="mt-3 grid grid-cols-3 gap-2 text-xs border-t border-dashed border-gray-400 pt-2">
                <p>
                  <b>Weight:</b><br />
                  {order.slicingResult.weightGrams.toFixed(1)} g
                </p>
                <p>
                  <b>Time:</b><br />
                  {formatSeconds(order.slicingResult.printTimeSeconds)}
                </p>
                <p>
                  <b>Price:</b><br />
                  {order.slicingResult.price.amount} {order.slicingResult.price.currency}
                </p>
              </div>
            )}

            {order.errorMessage && (
              <p className="mt-2 border border-red-500 bg-red-100 p-1 text-xs text-red-800 font-bold">
                Error: {order.errorMessage}
              </p>
            )}

            <p className="mt-2 text-xs text-gray-500 italic">Updated {formatAgo(order.updatedAt)}</p>
          </article>
        ))}
      </div>
    </Card>
  );
}
