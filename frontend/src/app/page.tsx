"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import GlassyCard from "@/components/shared/GlassyCard";
import StatusBadge from "@/components/shared/StatusBadge";
import PriceDisplay from "@/components/shared/PriceDisplay";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  Shield,
  AlertTriangle,
  Zap,
  BarChart3,
} from "lucide-react";
import { useEffect } from "react";
import { wsClient } from "@/lib/websocket";

export default function Dashboard() {
  const { data: portfolio, isLoading: portLoading } = useQuery({
    queryKey: ["portfolio"],
    queryFn: api.portfolio,
  });

  const { data: positions } = useQuery({
    queryKey: ["positions"],
    queryFn: api.positions,
  });

  const { data: signals } = useQuery({
    queryKey: ["signals"],
    queryFn: api.signals,
  });

  const { data: risk } = useQuery({
    queryKey: ["risk"],
    queryFn: api.riskStatus,
  });

  const { data: orders } = useQuery({
    queryKey: ["orders"],
    queryFn: api.orders,
  });

  useEffect(() => {
    wsClient.connect();
    return () => wsClient.disconnect();
  }, []);

  const activeSignals =
    signals?.filter((s) => s.verdict === "BUY_STARTER" && s.approved !== false) || [];
  const openOrders = orders?.filter((o) => o.status === "PENDING" || o.status === "SUBMITTED") || [];

  const isUp = (portfolio?.day_pnl_pct ?? 0) >= 0;
  const isDayUp = (portfolio?.day_pnl ?? 0) >= 0;
  const isTotalUp = (portfolio?.total_pnl ?? 0) >= 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-text-primary">Dashboard</h2>
          <p className="text-sm text-text-muted mt-1">
            Portfolio overview &amp; market status
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs">
            <span
              className={`status-dot ${
                risk?.broker_connected ? "status-dot-green" : "status-dot-red"
              }`}
            />
            <span className="text-text-secondary">
              {risk?.broker_connected ? "Connected" : "Disconnected"}
            </span>
          </div>
          {risk?.kill_switch_enabled && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-red/10 border border-accent-red/30 text-accent-red text-xs font-medium">
              <AlertTriangle size={14} />
              KILL SWITCH ACTIVE
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <GlassyCard neon="green">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider mb-1">
                Portfolio Value
              </p>
              {portLoading ? (
                <div className="h-7 w-28 bg-surface-hover animate-pulse rounded" />
              ) : (
                <p className="text-2xl font-bold font-mono text-text-primary">
                  <PriceDisplay value={portfolio?.total_value} prefix="$" />
                </p>
              )}
            </div>
            <DollarSign size={24} className="text-accent-green/40" />
          </div>
        </GlassyCard>

        <GlassyCard>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider mb-1">
                Day P&amp;L
              </p>
              {portLoading ? (
                <div className="h-7 w-28 bg-surface-hover animate-pulse rounded" />
              ) : (
                <div className="flex items-baseline gap-2">
                  <p
                    className={`text-2xl font-bold font-mono ${
                      isDayUp ? "value-up" : "value-down"
                    }`}
                  >
                    <PriceDisplay value={portfolio?.day_pnl} prefix="$" colorize />
                  </p>
                  <span
                    className={`text-sm font-mono ${
                      isUp ? "value-up" : "value-down"
                    }`}
                  >
                    <PriceDisplay value={portfolio?.day_pnl_pct} suffix="%" colorize />
                  </span>
                </div>
              )}
            </div>
            {isDayUp ? (
              <TrendingUp size={24} className="text-accent-green/40" />
            ) : (
              <TrendingDown size={24} className="text-accent-red/40" />
            )}
          </div>
        </GlassyCard>

        <GlassyCard>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider mb-1">
                Cash
              </p>
              {portLoading ? (
                <div className="h-7 w-28 bg-surface-hover animate-pulse rounded" />
              ) : (
                <p className="text-2xl font-bold font-mono text-text-primary">
                  <PriceDisplay value={portfolio?.cash} prefix="$" />
                </p>
              )}
            </div>
            <BarChart3 size={24} className="text-accent-blue/40" />
          </div>
        </GlassyCard>

        <GlassyCard>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider mb-1">
                Drawdown
              </p>
              {portLoading ? (
                <div className="h-7 w-28 bg-surface-hover animate-pulse rounded" />
              ) : (
                <div>
                  <p
                    className={`text-2xl font-bold font-mono ${
                      (portfolio?.drawdown_pct ?? 0) > 5
                        ? "value-down"
                        : "text-text-primary"
                    }`}
                  >
                    <PriceDisplay value={portfolio?.drawdown_pct} suffix="%" />
                  </p>
                </div>
              )}
            </div>
            <Activity size={24} className="text-accent-amber/40" />
          </div>
        </GlassyCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2">
          <GlassyCard title="Active Signals">
            {activeSignals.length === 0 ? (
              <div className="py-8 text-center text-text-muted text-sm">
                No active signals. Run the screener from the Signals page.
              </div>
            ) : (
              <div className="space-y-2">
                {activeSignals.slice(0, 5).map((sig) => (
                  <div
                    key={sig.id}
                    className="flex items-center justify-between py-2 px-3 rounded-lg bg-surface-hover/50"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono font-bold text-text-primary text-sm">
                        {sig.symbol}
                      </span>
                      <StatusBadge status={sig.verdict} />
                    </div>
                    <div className="flex items-center gap-4 text-xs font-mono text-text-secondary">
                      <span>
                        Score:{" "}
                        <span className="text-accent-green">
                          {sig.total_score}
                        </span>
                      </span>
                      <span>
                        Entry:{" "}
                        <PriceDisplay value={sig.entry_min} prefix="$" />
                      </span>
                      <span>
                        Stop:{" "}
                        <PriceDisplay value={sig.stop_level} prefix="$" />
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </GlassyCard>
        </div>

        <div className="space-y-4">
          <GlassyCard title="Open Orders">
            {openOrders.length === 0 ? (
              <p className="text-sm text-text-muted py-4 text-center">
                No open orders
              </p>
            ) : (
              <div className="space-y-2">
                {openOrders.map((o) => (
                  <div
                    key={o.id}
                    className="flex items-center justify-between py-1.5"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm">{o.symbol}</span>
                      <span
                        className={`text-xs ${
                          o.side === "BUY" ? "value-up" : "value-down"
                        }`}
                      >
                        {o.side}
                      </span>
                    </div>
                    <div className="text-xs text-text-muted font-mono">
                      {o.quantity} @ <PriceDisplay value={o.limit_price} prefix="$" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </GlassyCard>

          <GlassyCard title="Risk Status">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-text-secondary">Kill Switch</span>
                <span
                  className={`font-mono text-xs ${
                    risk?.kill_switch_enabled
                      ? "text-accent-red"
                      : "text-accent-green"
                  }`}
                >
                  {risk?.kill_switch_enabled ? "ACTIVE" : "INACTIVE"}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-text-secondary">Daily Loss</span>
                <span className="font-mono text-xs text-text-primary">
                  <PriceDisplay value={risk?.daily_loss_pct} suffix="%" />
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-text-secondary">Drawdown</span>
                <span className="font-mono text-xs text-text-primary">
                  <PriceDisplay value={risk?.drawdown_pct} suffix="%" />
                </span>
              </div>
            </div>
          </GlassyCard>
        </div>
      </div>

      <GlassyCard title="Recent Positions">
        {positions && positions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-text-muted text-xs uppercase tracking-wider border-b border-surface-border">
                  <th className="text-left py-2 pr-4">Symbol</th>
                  <th className="text-right py-2 pr-4">Qty</th>
                  <th className="text-right py-2 pr-4">Avg Cost</th>
                  <th className="text-right py-2 pr-4">Price</th>
                  <th className="text-right py-2 pr-4">Unrealized P&L</th>
                  <th className="text-right py-2 pr-4">% of Portfolio</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => (
                  <tr
                    key={pos.id}
                    className="border-b border-surface-border/50 hover:bg-surface-hover/30"
                  >
                    <td className="py-2.5 pr-4 font-mono font-medium">
                      {pos.symbol}
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono">
                      {pos.quantity}
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono">
                      <PriceDisplay value={pos.avg_cost} prefix="$" />
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono">
                      <PriceDisplay value={pos.current_price} prefix="$" />
                    </td>
                    <td
                      className={`py-2.5 pr-4 text-right font-mono ${
                        (pos.unrealized_pnl ?? 0) >= 0
                          ? "value-up"
                          : "value-down"
                      }`}
                    >
                      <PriceDisplay value={pos.unrealized_pnl} prefix="$" />
                    </td>
                    <td className="py-2.5 text-right font-mono text-text-secondary">
                      <PriceDisplay value={pos.position_pct} suffix="%" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-text-muted py-4 text-center">
            No positions
          </p>
        )}
      </GlassyCard>
    </div>
  );
}
