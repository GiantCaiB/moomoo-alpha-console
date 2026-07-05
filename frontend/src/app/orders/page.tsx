"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { isReadOnlyMode } from "@/lib/readonly";
import { useBrokerHealth } from "@/app/providers";
import GlassyCard from "@/components/shared/GlassyCard";
import PriceDisplay from "@/components/shared/PriceDisplay";
import StatusBadge from "@/components/shared/StatusBadge";
import { ShieldBan } from "lucide-react";

export default function OrdersPage() {
  const queryClient = useQueryClient();
  const { health } = useBrokerHealth();
  const readOnly = isReadOnlyMode(health);

  const { data: orders, isLoading } = useQuery({
    queryKey: ["orders"],
    queryFn: api.orders,
    refetchInterval: 15000,
  });

  const cancelMutation = useMutation({
    mutationFn: api.cancelOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });

  const pending = orders?.filter((o) => o.status === "PENDING") || [];
  const submitted = orders?.filter((o) => o.status === "SUBMITTED") || [];
  const filled = orders?.filter((o) => o.status === "FILLED") || [];
  const cancelled = orders?.filter((o) => o.status === "CANCELLED") || [];
  const rejected = orders?.filter((o) => o.status === "REJECTED") || [];

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-text-primary">Orders</h2>
        <p className="text-sm text-text-muted mt-1">
          Open and historical orders from moomoo. Read-only.
        </p>
      </div>

      {readOnly && (
        <div className="mb-4 px-4 py-2.5 rounded-xl bg-accent-amber/10 border border-accent-amber/25 text-accent-amber text-sm flex items-center gap-2">
          <ShieldBan size={16} />
          Read-only: manage or cancel orders in the moomoo app.
        </div>
      )}

      {isLoading ? (
        <div className="h-40 bg-surface-hover animate-pulse rounded-xl" />
      ) : orders && orders.length > 0 ? (
        <div className="space-y-4">
          {pending.length > 0 && (
            <GlassyCard title="Pending" neon="amber">
              <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[820px]">
                  <thead>
                    <tr className="tableHeader">
                      <th className="text-left py-2 pr-4">Symbol</th>
                      <th className="text-center py-2 pr-4">Side</th>
                      <th className="text-center py-2 pr-4">Status</th>
                      <th className="text-right py-2 pr-4">Qty</th>
                      <th className="text-right py-2 pr-4">Limit Price</th>
                      <th className="text-right py-2 pr-4">Filled</th>
                      <th className="text-right py-2 pr-4">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pending.map((o) => (
                      <OrderRow
                        key={o.id}
                        order={o}
                        readOnly={readOnly}
                        onCancel={
                          !readOnly && !cancelMutation.isPending
                            ? () => cancelMutation.mutate(o.id)
                            : undefined
                        }
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </GlassyCard>
          )}

          {submitted.length > 0 && (
            <GlassyCard title="Submitted">
              <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[820px]">
                  <thead>
                    <tr className="tableHeader">
                      <th className="text-left py-2 pr-4">Symbol</th>
                      <th className="text-center py-2 pr-4">Side</th>
                      <th className="text-center py-2 pr-4">Status</th>
                      <th className="text-right py-2 pr-4">Qty</th>
                      <th className="text-right py-2 pr-4">Limit Price</th>
                      <th className="text-right py-2 pr-4">Filled</th>
                      <th className="text-right py-2 pr-4">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {submitted.map((o) => (
                      <OrderRow key={o.id} order={o} readOnly={readOnly} />
                    ))}
                  </tbody>
                </table>
              </div>
            </GlassyCard>
          )}

          {filled.length > 0 && (
            <GlassyCard title="Filled">
              <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[820px]">
                  <thead>
                    <tr className="tableHeader">
                      <th className="text-left py-2 pr-4">Symbol</th>
                      <th className="text-center py-2 pr-4">Side</th>
                      <th className="text-center py-2 pr-4">Status</th>
                      <th className="text-right py-2 pr-4">Qty</th>
                      <th className="text-right py-2 pr-4">Limit Price</th>
                      <th className="text-right py-2 pr-4">Filled</th>
                      <th className="text-right py-2 pr-4">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filled.map((o) => (
                      <OrderRow key={o.id} order={o} readOnly={readOnly} />
                    ))}
                  </tbody>
                </table>
              </div>
            </GlassyCard>
          )}

          {cancelled.length > 0 && (
            <GlassyCard title="Cancelled">
              <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[820px]">
                  <thead>
                    <tr className="tableHeader">
                      <th className="text-left py-2 pr-4">Symbol</th>
                      <th className="text-center py-2 pr-4">Side</th>
                      <th className="text-center py-2 pr-4">Status</th>
                      <th className="text-right py-2 pr-4">Qty</th>
                      <th className="text-right py-2 pr-4">Limit Price</th>
                      <th className="text-right py-2 pr-4">Filled</th>
                      <th className="text-right py-2 pr-4">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cancelled.map((o) => (
                      <OrderRow key={o.id} order={o} readOnly={readOnly} />
                    ))}
                  </tbody>
                </table>
              </div>
            </GlassyCard>
          )}

          {rejected.length > 0 && (
            <GlassyCard title="Rejected" neon="red">
              <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[820px]">
                  <thead>
                    <tr className="tableHeader">
                      <th className="text-left py-2 pr-4">Symbol</th>
                      <th className="text-center py-2 pr-4">Side</th>
                      <th className="text-center py-2 pr-4">Status</th>
                      <th className="text-right py-2 pr-4">Qty</th>
                      <th className="text-right py-2 pr-4">Limit Price</th>
                      <th className="text-right py-2 pr-4">Filled</th>
                      <th className="text-right py-2 pr-4">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rejected.map((o) => (
                      <OrderRow key={o.id} order={o} readOnly={readOnly} />
                    ))}
                  </tbody>
                </table>
              </div>
            </GlassyCard>
          )}
        </div>
      ) : (
        <GlassyCard>
          <div className="text-center py-12 text-text-muted text-sm">
            No orders yet. Open orders are managed in moomoo.
          </div>
        </GlassyCard>
      )}
    </div>
  );
}

function OrderRow({
  order,
  onCancel,
  readOnly,
}: {
  order: any;
  onCancel?: () => void;
  readOnly?: boolean;
}) {
  return (
    <tr className="tableRow">
      <td className="py-2.5 pr-4 font-mono font-bold text-text-primary">{order.symbol}</td>
      <td className={`py-2.5 pr-4 text-center font-mono text-sm ${order.side === "BUY" ? "value-up" : "value-down"}`}>{order.side}</td>
      <td className="py-2.5 pr-4"><StatusBadge status={order.status} /></td>
      <td className="tableCellNumeric">{order.quantity ?? "--"}</td>
      <td className="tableCellNumeric"><PriceDisplay value={order.limit_price} prefix="$" /></td>
      <td className="tableCellNumeric text-xs">{order.filled_quantity}/{order.quantity}</td>
      <td className="py-2.5 text-right">
        {readOnly ? (
          <span className="inline-flex items-center gap-1 text-text-muted text-xs">
            <ShieldBan size={12} />
            Locked
          </span>
        ) : onCancel ? (
          <button
            onClick={onCancel}
            className="px-2 py-1 rounded text-accent-red hover:bg-accent-red/10 text-xs
                       transition-colors"
          >
            Cancel
          </button>
        ) : (
          <span className="text-text-muted text-xs">--</span>
        )}
      </td>
    </tr>
  );
}
