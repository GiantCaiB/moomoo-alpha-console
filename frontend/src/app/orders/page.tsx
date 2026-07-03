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
        <h2 className="text-2xl font-bold text-text-primary">Orders</h2>
        <p className="text-sm text-text-muted mt-1">
          Order history &amp; status ({orders?.length || 0} total)
        </p>
      </div>

      {readOnly && (
        <div className="mb-4 px-4 py-2.5 rounded-lg bg-accent-amber/10 border border-accent-amber/30 text-accent-amber text-sm flex items-center gap-2">
          <ShieldBan size={16} />
          {health?.account_environment === "moomoo_real"
            ? "MOOMOO REAL READ-ONLY — Orders are displayed from moomoo. Manage/cancel orders in the moomoo app."
            : "Read-only mode — orders are displayed for reference. Order actions are disabled."}
        </div>
      )}

      {isLoading ? (
        <div className="h-40 bg-surface-hover animate-pulse rounded-xl" />
      ) : (
        <div className="space-y-4">
          {rejected.length > 0 && (
            <GlassyCard title="Rejected" neon="red">
              {rejected.map((o) => (
                <OrderRow key={o.id} order={o} readOnly={readOnly} />
              ))}
            </GlassyCard>
          )}

          {pending.length > 0 && (
            <GlassyCard title="Pending" neon="green">
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
            </GlassyCard>
          )}

          {submitted.length > 0 && (
            <GlassyCard title="Submitted">
              {submitted.map((o) => (
                <OrderRow key={o.id} order={o} readOnly={readOnly} />
              ))}
            </GlassyCard>
          )}

          {filled.length > 0 && (
            <GlassyCard title="Filled">
              {filled.map((o) => (
                <OrderRow key={o.id} order={o} readOnly={readOnly} />
              ))}
            </GlassyCard>
          )}

          {cancelled.length > 0 && (
            <GlassyCard title="Cancelled">
              {cancelled.map((o) => (
                <OrderRow key={o.id} order={o} readOnly={readOnly} />
              ))}
            </GlassyCard>
          )}

          {orders?.length === 0 && (
            <GlassyCard>
              <div className="text-center py-12 text-text-muted text-sm">
                No orders yet. Generate signals and approve them to create orders.
              </div>
            </GlassyCard>
          )}
        </div>
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
    <div className="flex items-center justify-between py-2.5 border-b border-surface-border/30 last:border-0">
      <div className="flex items-center gap-3">
        <span className="font-mono font-bold text-sm">{order.symbol}</span>
        <span
          className={`text-xs font-mono ${
            order.side === "BUY" ? "value-up" : "value-down"
          }`}
        >
          {order.side}
        </span>
        <StatusBadge status={order.status} />
      </div>
      <div className="flex items-center gap-4 text-xs font-mono text-text-secondary">
        <span>
          {order.quantity ?? "--"} @{" "}
          <PriceDisplay value={order.limit_price} prefix="$" />
        </span>
        <span>
          Filled: {order.filled_quantity}/{order.quantity}
        </span>
        {order.reason && (
          <span className="text-text-muted max-w-xs truncate" title={order.reason}>
            {order.reason}
          </span>
        )}
        {readOnly ? (
          <span className="text-text-muted text-xs italic">
            Read-only — cancel in moomoo app
          </span>
        ) : onCancel ? (
          <button
            onClick={onCancel}
            className="px-2 py-1 rounded text-accent-red hover:bg-accent-red/10 text-xs
                       transition-colors"
          >
            Cancel
          </button>
        ) : null}
      </div>
    </div>
  );
}
