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
import { useEffect, useState } from "react";
import Link from "next/link";
import { wsClient } from "@/lib/websocket";
import type { PositionResponse } from "@/lib/types";

export default function Cockpit() {
  const { health } = useBrokerHealth();

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

  const { data: positionSignals } = useQuery({
    queryKey: ["position-signals"],
    queryFn: () => api.positionSignals(),
  });

  const { data: risk } = useQuery({
    queryKey: ["risk"],
    queryFn: api.riskStatus,
  });

  const { data: marketData } = useQuery({
    queryKey: ["market-data-status"],
    queryFn: api.marketDataStatus,
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

  type SortKey = "symbol" | "quantity" | "avg_cost" | "current_price" | "market_value" | "unrealized_pnl" | "total_pnl" | "position_pct";
  const [sortKey, setSortKey] = useState<SortKey>("position_pct");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

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
  const displayedOpenOrders = openOrders.slice(0, 5);
  const positionAlerts = (positionSignals ?? []).filter(
    (sig) =>
      [
        "TRIM_PROFIT",
        "ENTER_TAIL_MODE",
        "TRIM_TAIL",
        "EXIT_TAIL",
        "REVIEW_POSITION",
        "STOP_ADDING",
        "REDUCE_RISK",
        "EXIT_POSITION",
      ].includes(sig.signal)
  );

  const isDayUp = (portfolio?.day_pnl ?? 0) >= 0;

  const isMoomooReal = env === "moomoo_real";
  const isMoomooSim = env === "moomoo_simulate";
  const isPaper = env === "paper";
  const connected = health?.connected ?? true;

  const bannerData = (() => {
    if (isMoomooReal && connected) {
      return {
        text: "REAL ACCOUNT · READ ONLY · Real moomoo account data is shown. No trades can be placed from this app.",
        icon: Database,
        className: "bg-accent-amber/10 border-accent-amber/30 text-accent-amber",
      };
    }
    if (isMoomooSim && connected) {
      return {
        text: "SIMULATED ACCOUNT · READ ONLY · Simulated moomoo account data is shown.",
        icon: Eye,
        className: "bg-accent-blue/10 border-accent-blue/30 text-accent-blue",
      };
    }
    if (isMoomoo && !connected) {
      return {
        text: "MOOMOO DISCONNECTED · Check OpenD connection. Account data unavailable.",
        icon: AlertTriangle,
        className: "bg-accent-red/10 border-accent-red/30 text-accent-red",
      };
    }
    if (isPaper) {
      return {
        text: "PAPER MODE · Simulated local paper trading only.",
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
          className={`mb-3 px-3.5 py-2 rounded-lg border flex items-center gap-2 text-xs font-medium ${bannerData.className}`}
        >
          <bannerData.icon size={18} />
          <span>{bannerData.text}</span>
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold text-text-primary">Cockpit</h2>
          <p className="text-sm text-text-muted mt-1">
            Account overview, active signals, position alerts, and risk status. · {isMoomooReal ? "Real Account" : isMoomooSim ? "Simulated Account" : isPaper ? "Paper Account" : "Mock Account"} · Read-only · {connected ? "Connected" : "Disconnected"}
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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
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
                Open Orders
              </p>
              {portLoading ? (
                <div className="h-7 w-28 bg-surface-hover animate-pulse rounded" />
              ) : (
                <div>
                  <p className="text-2xl font-bold font-mono text-text-primary">
                    {openOrders.length}
                  </p>
                  <p className="text-xs text-text-muted mt-1">Pending or submitted</p>
                </div>
              )}
            </div>
            <Activity size={24} className="text-accent-amber/40" />
          </div>
        </GlassyCard>

        <GlassyCard>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider mb-1">
                Read-only Status
              </p>
              <p className="text-2xl font-bold font-mono text-accent-amber">Active</p>
              <p className="text-xs text-text-muted mt-1">Trading actions are blocked</p>
            </div>
            <Shield size={24} className="text-accent-purple/40" />
          </div>
        </GlassyCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)] gap-x-6 gap-y-4 mb-6 items-start">
        <div className="order-1 lg:col-start-1 lg:row-start-1">
          <GlassyCard title="Entry Signal Highlights">
            {activeSignals.length === 0 ? (
              <div className="flex items-center justify-between gap-4 px-3 py-4 text-sm">
                <p className="text-text-muted">
                  No active entry alerts. Run Entry Screener to refresh new position ideas.
                </p>
                <Link href="/signals" className="shrink-0 text-xs font-medium text-accent-green hover:text-accent-green/80">
                  Run Screener →
                </Link>
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
                          Research signal only â€” generated from mock/local data
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </GlassyCard>
        </div>

        <div className="order-3 lg:col-start-2 lg:row-start-1 lg:row-span-2 space-y-4">
          <GlassyCard title="Open Orders">
            {openOrders.length === 0 ? (
              <p className="text-sm text-text-muted py-4 text-center">
                No open orders
              </p>
            ) : (
              <div className="space-y-2">
                {displayedOpenOrders.map((o) => (
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
            {openOrders.length > 5 && (
              <div className="mt-3 border-t border-surface-border/60 pt-3 text-right">
                <Link href="/orders" className="text-xs font-medium text-accent-blue hover:text-accent-blue/80">
                  View all orders →
                </Link>
              </div>
            )}
          </GlassyCard>

          <GlassyCard title="Position Management Alerts">
            {positionAlerts.length === 0 ? (
              <p className="text-sm text-text-muted py-4 text-center">
                No active position management alerts.
              </p>
            ) : (
              <div className="space-y-2">
                {positionAlerts.slice(0, 5).map((sig) => {
                  const badge = getSourceBadge(sig.data_source);
                  return (
                    <div key={`${sig.symbol}-${sig.generated_at}`} className="py-2 px-3 rounded-lg bg-surface-hover/50">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-text-primary text-sm">{sig.symbol}</span>
                          <StatusBadge status={sig.signal} />
                        </div>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${badge.className}`}>
                          {badge.label}
                        </span>
                      </div>
                      <div className="mt-1 text-xs text-text-secondary font-mono flex flex-wrap gap-3">
                        <span>Qty: {formatQuantity(sig.quantity)}</span>
                        <span>Gain: {formatPercent(sig.gain_pct)}</span>
                        <span>{sig.suggested_action ?? "Hold"}</span>
                      </div>
                    </div>
                  );
                })}
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

          <GlassyCard title="Data Health">
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-text-secondary">Moomoo</span>
                <span className={`text-xs font-medium px-2 py-1 rounded-full border ${connected ? "bg-accent-green/10 text-accent-green border-accent-green/25" : "bg-accent-red/10 text-accent-red border-accent-red/25"}`}>
                  {connected ? "Connected" : "Disconnected"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-secondary">Market Data</span>
                <span className="text-xs font-medium px-2 py-1 rounded-full border bg-accent-cyan/10 text-accent-cyan border-accent-cyan/25">
                  {marketData?.provider?.toUpperCase() ?? "YFINANCE"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-secondary">Cache</span>
                <span className={`text-xs font-medium px-2 py-1 rounded-full border ${marketData?.cache_enabled ? "bg-accent-green/10 text-accent-green border-accent-green/25" : "bg-surface-hover text-text-muted border-surface-border"}`}>
                  {marketData?.cache_enabled ? "Ready" : "Disabled"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-secondary">Read-only</span>
                <span className="text-xs font-medium px-2 py-1 rounded-full border bg-accent-amber/10 text-accent-amber border-accent-amber/25">
                  Active
                </span>
              </div>
            </div>
          </GlassyCard>
        </div>
      <div className="order-2 lg:col-start-1 lg:row-start-2">
      <GlassyCard title="Portfolio Holdings">
        {(() => {
          const activePositions = positions?.filter((p) => (p.quantity ?? 0) > 0) ?? [];

          const getSortValue = (pos: PositionResponse, key: SortKey): number | string => {
            switch (key) {
              case "symbol": return pos.symbol;
              case "quantity": return pos.quantity ?? 0;
              case "avg_cost": return pos.avg_cost ?? 0;
              case "current_price": return pos.current_price ?? 0;
              case "market_value": return (pos.quantity ?? 0) * (pos.current_price ?? 0);
              case "unrealized_pnl": return pos.unrealized_pnl ?? 0;
              case "total_pnl": return pos.total_pnl ?? 0;
              case "position_pct": return pos.position_pct ?? 0;
            }
          };

           const sortedPositions = [...activePositions].sort((a, b) => {
            const va = getSortValue(a, sortKey);
            const vb = getSortValue(b, sortKey);
            let cmp = 0;
            if (typeof va === "string" && typeof vb === "string") {
              cmp = va.localeCompare(vb);
            } else {
              cmp = (va as number) - (vb as number);
            }
            return sortDir === "asc" ? cmp : -cmp;
           });

           const topWeightedSymbols = new Set(
             [...activePositions]
               .sort((a, b) => (b.position_pct ?? 0) - (a.position_pct ?? 0))
               .slice(0, 3)
               .map((position) => position.symbol)
           );

          const totalMktValue = activePositions.reduce(
            (s, p) => s + (p.quantity ?? 0) * (p.current_price ?? 0),
            0
          );

          const sortTh = (label: string, key: SortKey, align: string) => {
            const isActive = sortKey === key;
            return (
              <th
                className={`${align} py-2 pr-4 cursor-pointer select-none hover:text-text-primary transition-colors`}
                onClick={() => {
                  if (sortKey === key) {
                    setSortDir((d) => (d === "asc" ? "desc" : "asc"));
                  } else {
                    setSortKey(key);
                    setSortDir("asc");
                  }
                }}
              >
                <span className="inline-flex items-center gap-1">
                  {label}
                  {isActive && <span className="text-[10px]">{sortDir === "asc" ? "▲" : "▼"}</span>}
                </span>
              </th>
            );
          };

          return sortedPositions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="tableHeader bg-surface-hover/60">
                    {sortTh("Symbol", "symbol", "text-left")}
                    {sortTh("Qty", "quantity", "text-right")}
                    {sortTh("Avg Cost", "avg_cost", "text-right")}
                    {sortTh("Price", "current_price", "text-right")}
                    {sortTh("Mkt Value", "market_value", "text-right")}
                    {sortTh("Unrealized P&L", "unrealized_pnl", "text-right")}
                    {sortTh("Total P&L", "total_pnl", "text-right")}
                    {sortTh("% of Portfolio", "position_pct", "text-right")}
                  </tr>
                </thead>
                <tbody>
                  {sortedPositions.map((pos) => (
                    <tr
                      key={pos.id}
                      className={`tableRow ${topWeightedSymbols.has(pos.symbol) ? "bg-accent-blue/5" : ""}`}
                    >
                      <td className="tableCell font-medium">
                        {pos.symbol}
                      </td>
                      <td className="tableCellNumeric">
                        {formatQuantity(pos.quantity)}
                      </td>
                      <td className="tableCellNumeric">
                        {formatPrice(pos.avg_cost)}
                      </td>
                      <td className="tableCellNumeric">
                        {formatPrice(pos.current_price)}
                      </td>
                      <td className="tableCellNumeric">
                        {formatPrice((pos.quantity ?? 0) * (pos.current_price ?? 0))}
                      </td>
                      <td
                        className={`tableCellNumeric ${
                          (pos.unrealized_pnl ?? 0) >= 0
                            ? "value-up"
                            : "value-down"
                        }`}
                      >
                        {formatMoney(pos.unrealized_pnl)}
                      </td>
                      <td
                        className={`tableCellNumeric ${
                          (pos.total_pnl ?? 0) >= 0 ? "value-up" : "value-down"
                        }`}
                      >
                        {formatMoney(pos.total_pnl)}
                      </td>
                      <td className="tableCellNumeric text-text-secondary">
                        {formatPercent(pos.position_pct)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-surface-border bg-surface-hover/60 font-semibold text-text-primary">
                    <td className="py-2.5 pr-4">Total</td>
                    <td className="tableCellNumeric">
                      {formatQuantity(activePositions.reduce((s, p) => s + (p.quantity ?? 0), 0))}
                    </td>
                    <td className="tableCellNumeric text-text-muted">--</td>
                    <td className="tableCellNumeric text-text-muted">--</td>
                    <td className="tableCellNumeric">
                      {formatPrice(totalMktValue)}
                    </td>
                    <td className="tableCellNumeric">
                      {formatMoney(activePositions.reduce((s, p) => s + (p.unrealized_pnl ?? 0), 0))}
                    </td>
                    <td className="tableCellNumeric">
                      {formatMoney(activePositions.reduce((s, p) => s + (p.total_pnl ?? 0), 0))}
                    </td>
                    <td className="tableCellNumeric">
                      {formatPercent(activePositions.reduce((s, p) => s + (p.position_pct ?? 0), 0))}
                    </td>
                  </tr>
                </tfoot>
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
      </div>
    </div>
  );
}


