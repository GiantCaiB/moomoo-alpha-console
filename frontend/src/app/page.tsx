"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useBrokerHealth } from "@/app/providers";
import GlassyCard from "@/components/shared/GlassyCard";
import StatusBadge from "@/components/shared/StatusBadge";
import PriceDisplay from "@/components/shared/PriceDisplay";
import {
  formatMoney,
  formatPercent,
  formatQuantity,
  formatPrice,
} from "@/lib/format";
import { getSourceBadge } from "@/lib/source_badge";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  Shield,
  AlertTriangle,
  BarChart3,
  Database,
  Eye,
  FlaskConical,
} from "lucide-react";
import { useEffect } from "react";
import { wsClient } from "@/lib/websocket";

export default function Dashboard() {
  const { health, isLoading: healthLoading } = useBrokerHealth();

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
    queryFn: () => api.signals(),
  });

  const { data: risk } = useQuery({
    queryKey: ["risk"],
    queryFn: api.riskStatus,
  });

  const { data: orders } = useQuery({
    queryKey: ["orders"],
    queryFn: api.orders,
  });

  const { data: universe } = useQuery({
    queryKey: ["trading-universe"],
    queryFn: api.tradingUniverse,
  });
  const universeSymbols = universe?.symbols ?? [];

  useEffect(() => {
    wsClient.connect();
    return () => wsClient.disconnect();
  }, []);

  const env = health?.account_environment ?? "mock";
  const isMoomoo = env.startsWith("moomoo");

  const rawActiveSignals =
    signals?.filter(
      (s) =>
        s.verdict === "BUY_STARTER" &&
        s.approved !== false &&
        (!isMoomoo || (
          s.data_source === "moomoo" &&
          s.is_real_market_data === true &&
          s.has_error !== true &&
          universeSymbols.includes(s.symbol)
        ))
    ) || [];
  const activeSignals = (() => {
    const latestBySymbol = new Map<string, (typeof rawActiveSignals)[number]>();
    for (const sig of rawActiveSignals) {
      const existing = latestBySymbol.get(sig.symbol);
      if (!existing || new Date(sig.created_at) > new Date(existing.created_at)) {
        latestBySymbol.set(sig.symbol, sig);
      }
    }
    return Array.from(latestBySymbol.values());
  })();
  const openOrders = orders?.filter((o) => o.status === "PENDING" || o.status === "SUBMITTED") || [];

  const isDayUp = (portfolio?.day_pnl ?? 0) >= 0;

  const isMoomooReal = env === "moomoo_real";
  const isMoomooSim = env === "moomoo_simulate";
  const isPaper = env === "paper";
  const isMock = env === "mock";
  const connected = health?.connected ?? true;

  const bannerData = (() => {
    if (isMoomooReal && connected) {
      return {
        text: "MOOMOO REAL READ-ONLY — Real moomoo account data shown. Live trading disabled.",
        icon: Database,
        className: "bg-accent-amber/10 border-accent-amber/30 text-accent-amber",
      };
    }
    if (isMoomooSim && connected) {
      return {
        text: "MOOMOO SIMULATE READ-ONLY — Moomoo simulated account data shown. Live trading disabled.",
        icon: Eye,
        className: "bg-accent-blue/10 border-accent-blue/30 text-accent-blue",
      };
    }
    if (isMoomoo && !connected) {
      return {
        text: "MOOMOO DISCONNECTED — Check OpenD connection. Account data unavailable.",
        icon: AlertTriangle,
        className: "bg-accent-red/10 border-accent-red/30 text-accent-red",
      };
    }
    if (isPaper) {
      return {
        text: "PAPER MODE — Simulated local paper trading only.",
        icon: FlaskConical,
        className: "bg-accent-purple/10 border-accent-purple/30 text-accent-purple",
      };
    }
    return null;
  })();

  return (
    <div>
      {bannerData && (
        <div
          className={`mb-4 px-4 py-2.5 rounded-lg border flex items-center gap-2 text-sm font-medium ${bannerData.className}`}
        >
          <bannerData.icon size={18} />
          <span>{bannerData.text}</span>
        </div>
      )}

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
                connected ? "status-dot-green" : "status-dot-red"
              }`}
            />
            <span className="text-text-secondary">
              {connected ? "Connected" : "Disconnected"}
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
        <GlassyCard neon={isMoomooReal ? "green" : "none"}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider mb-1">
                Portfolio Value
                {isMoomooReal && (
                  <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-accent-green/20 text-accent-green border border-accent-green/30">
                    REAL
                  </span>
                )}
                {isMoomooSim && (
                  <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-accent-blue/20 text-accent-blue border border-accent-blue/30">
                    SIM
                  </span>
                )}
              </p>
              {portLoading ? (
                <div className="h-7 w-28 bg-surface-hover animate-pulse rounded" />
              ) : (
                <p className="text-2xl font-bold font-mono text-text-primary">
                  {formatMoney(portfolio?.total_value, portfolio?.currency)}
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
                    {formatMoney(portfolio?.day_pnl)}
                  </p>
                  <span
                    className={`text-sm font-mono ${
                      isDayUp ? "value-up" : "value-down"
                    }`}
                  >
                    {formatPercent(portfolio?.day_pnl_pct)}
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
                  {formatMoney(portfolio?.cash, portfolio?.currency)}
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
                    {formatPercent(portfolio?.drawdown_pct)}
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
                {isMoomoo
                  ? "Run screener to generate signals from moomoo market data."
                  : "No active signals. Run the screener from the Signals page."}
              </div>
            ) : (
              <div className="space-y-2">
                {activeSignals.slice(0, 5).map((sig) => {
                  const badge = getSourceBadge(sig.data_source);
                  return (
                    <div
                      key={sig.id}
                      className="py-2 px-3 rounded-lg bg-surface-hover/50"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-text-primary text-sm">
                            {sig.symbol}
                          </span>
                          <StatusBadge status={sig.verdict} />
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${badge.className}`}>
                            {badge.label}
                          </span>
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
                      {!sig.is_real_market_data && (
                        <p className="text-[11px] text-accent-amber mt-1">
                          Research signal only — generated from mock/local data
                        </p>
                      )}
                    </div>
                  );
                })}
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
                      {formatQuantity(o.quantity)} @ {formatPrice(o.limit_price)}
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
                  {formatPercent(risk?.daily_loss_pct)}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-text-secondary">Drawdown</span>
                <span className="font-mono text-xs text-text-primary">
                  {formatPercent(risk?.drawdown_pct)}
                </span>
              </div>
            </div>
          </GlassyCard>
        </div>
      </div>

      <GlassyCard title="Recent Positions">
        {(() => {
          const activePositions = positions?.filter((p) => (p.quantity ?? 0) > 0) ?? [];
          return activePositions.length > 0 ? (
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
                  {activePositions.map((pos) => (
                    <tr
                      key={pos.id}
                      className="border-b border-surface-border/50 hover:bg-surface-hover/30"
                    >
                      <td className="py-2.5 pr-4 font-mono font-medium">
                        {pos.symbol}
                      </td>
                      <td className="py-2.5 pr-4 text-right font-mono">
                        {formatQuantity(pos.quantity)}
                      </td>
                      <td className="py-2.5 pr-4 text-right font-mono">
                        {formatPrice(pos.avg_cost)}
                      </td>
                      <td className="py-2.5 pr-4 text-right font-mono">
                        {formatPrice(pos.current_price)}
                      </td>
                      <td
                        className={`py-2.5 pr-4 text-right font-mono ${
                          (pos.unrealized_pnl ?? 0) >= 0
                            ? "value-up"
                            : "value-down"
                        }`}
                      >
                        {formatMoney(pos.unrealized_pnl)}
                      </td>
                      <td className="py-2.5 text-right font-mono text-text-secondary">
                        {formatPercent(pos.position_pct)}
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
          );
        })()}
      </GlassyCard>
    </div>
  );
}
