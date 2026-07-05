"use client";

import { useMemo, useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, RotateCcw, Shield, Sparkles, BookOpen } from "lucide-react";
import { api } from "@/lib/api";
import { formatPercent, formatQuantity } from "@/lib/format";
import GlassyCard from "@/components/shared/GlassyCard";
import PriceDisplay from "@/components/shared/PriceDisplay";
import StatusBadge from "@/components/shared/StatusBadge";
import { getSourceBadge } from "@/lib/source_badge";
import StrategyRulesModal from "@/components/shared/StrategyRulesModal";
import type { StrategyProfileResponse } from "@/lib/types";

type PortfolioTab = "holdings" | "management";

function trendStatus(signal: string, weeklyClose: number | null, weeklySma20: number | null, weeklySma30: number | null) {
  if (signal === "EXIT_POSITION") return "Exit review";
  if (signal === "REDUCE_RISK") return "Risk reduction";
  if (signal === "STOP_ADDING") return "No adds";
  if (signal === "REVIEW_POSITION") return "Review";
  if (signal === "EXIT_TAIL") return "Tail broken";
  if (signal === "TRIM_TAIL") return "Weak tail";
  if (signal === "HOLD_TAIL") return "Tail intact";
  if (weeklyClose === null || weeklySma20 === null || weeklySma30 === null) return "--";
  if (weeklyClose < weeklySma30) return "Below SMA30";
  if (weeklyClose < weeklySma20) return "Between SMA20/SMA30";
  return "Above SMA20";
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
        active
          ? "bg-surface-hover text-text-primary border-surface-border"
          : "bg-surface-hover/40 text-text-secondary border-surface-border/70 hover:text-text-primary"
      }`}
    >
      {children}
    </button>
  );
}

function PositionChip({ unrealizedPnl, weight }: { unrealizedPnl: number | null; weight: number }) {
  const chipClass = "text-[10px] px-1.5 py-0.5 rounded min-w-[5rem] text-center";
  if ((unrealizedPnl ?? 0) > 0) {
    return <span className={`${chipClass} bg-accent-green/15 text-accent-green border border-accent-green/20`}>Winning</span>;
  }
  if ((unrealizedPnl ?? 0) < 0) {
    return <span className={`${chipClass} bg-accent-red/15 text-accent-red border border-accent-red/20`}>Losing</span>;
  }
  if (weight >= 20) {
    return <span className={`${chipClass} bg-accent-purple/15 text-accent-purple border border-accent-purple/20`}>Large Weight</span>;
  }
  return <span className={`${chipClass} bg-surface-hover text-text-muted border border-surface-border/70`}>Small Position</span>;
}

function SignalSection({
  title,
  rows,
  emptyText,
}: {
  title: string;
  rows: Array<any>;
  emptyText: string;
}) {
  return (
    <GlassyCard title={title}>
      {rows.length === 0 ? (
        <div className="py-8 text-center text-text-muted text-sm">{emptyText}</div>
      ) : (
        <div className="space-y-3">
          {rows.map((row) => (
            <GlassyCard key={`${row.symbol}-${row.generated_at}`} className="p-0 overflow-hidden">
              <details className="group">
                <summary className="cursor-pointer list-none px-5 py-4 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-bold text-text-primary">{row.symbol}</span>
                    <StatusBadge status={row.signal} />
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${getSourceBadge(row.data_source).className}`}>
                      {getSourceBadge(row.data_source).label}
                    </span>
                    <span className="text-[10px] text-text-muted font-mono">
                      {row.generated_at ? new Date(row.generated_at).toLocaleString() : "--"}
                    </span>
                  </div>
                  <div className="text-xs text-text-secondary font-mono">
                    Gain {formatPercent(row.gain_pct)} · Drawdown {formatPercent(row.drawdown_from_high)}
                  </div>
                </summary>
                <div className="px-5 pb-5 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  <div className="space-y-1 text-text-secondary">
                    <p><span className="text-text-muted">Avg cost:</span> <PriceDisplay value={row.avg_cost} prefix="$" /></p>
                    <p><span className="text-text-muted">Current price:</span> <PriceDisplay value={row.current_price} prefix="$" /></p>
                    <p><span className="text-text-muted">Gain %:</span> {formatPercent(row.gain_pct)}</p>
                    <p><span className="text-text-muted">Original cost basis:</span> <PriceDisplay value={row.original_cost_basis} prefix="$" /></p>
                    <p><span className="text-text-muted">Highest price since entry:</span> <PriceDisplay value={row.highest_price_since_entry} prefix="$" /></p>
                  </div>
                  <div className="space-y-1 text-text-secondary">
                    <p><span className="text-text-muted">Drawdown from high:</span> {formatPercent(row.drawdown_from_high)}</p>
                    <p><span className="text-text-muted">Weekly close:</span> <PriceDisplay value={row.weekly_close} prefix="$" /></p>
                    <p><span className="text-text-muted">Weekly SMA20:</span> <PriceDisplay value={row.weekly_sma20} prefix="$" /></p>
                    <p><span className="text-text-muted">Weekly SMA30:</span> <PriceDisplay value={row.weekly_sma30} prefix="$" /></p>
                    <p><span className="text-text-muted">Suggested trim %:</span> {row.suggested_trim_pct ?? "--"}</p>
                    <p><span className="text-text-muted">Suggested quantity:</span> {row.suggested_quantity ?? "--"}</p>
                  </div>
                  <div className="md:col-span-2 space-y-1 text-text-secondary">
                    <p><span className="text-text-muted">Reason:</span> {row.reason ?? "--"}</p>
                    <p><span className="text-text-muted">Price source:</span> {row.price_source}</p>
                    <p><span className="text-text-muted">Bar source:</span> {row.bar_source}</p>
                    <p><span className="text-text-muted">Generated at:</span> {new Date(row.generated_at).toLocaleString()}</p>
                  </div>
                  <div className="md:col-span-2 text-xs text-text-muted border-t border-surface-border/50 pt-3">
                    {row.signal === "ENTER_TAIL_MODE" && (
                      <p>Position is up 100%+. Consider recovering original cost basis and keeping remaining shares as a profit tail.</p>
                    )}
                    {row.signal === "TRIM_PROFIT" && (
                      <p>Staged profit trim. This does not mean the full position should be closed.</p>
                    )}
                    {row.signal === "REVIEW_POSITION" && (
                      <p>Review the position thesis and risk manually.</p>
                    )}
                    {row.signal === "STOP_ADDING" && (
                      <p>Do not add until the thesis and trend improve.</p>
                    )}
                    {row.signal === "REDUCE_RISK" && (
                      <p>Consider reducing exposure manually.</p>
                    )}
                    {row.signal === "EXIT_POSITION" && (
                      <p>Major risk threshold breached. Review exit manually.</p>
                    )}
                    {row.signal === "EXIT_TAIL" && (
                      <p>Tail trend appears broken. Consider exiting remaining tail manually.</p>
                    )}
                    {row.signal === "HOLD" && (
                      <p>HOLD means no position-management action is triggered. It is not a new buy signal.</p>
                    )}
                  </div>
                </div>
              </details>
            </GlassyCard>
          ))}
        </div>
      )}
    </GlassyCard>
  );
}

export default function PositionsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<PortfolioTab>("holdings");
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [rulesProfile, setRulesProfile] = useState<StrategyProfileResponse | null>(null);

  const { data: positionProfiles } = useQuery({
    queryKey: ["strategy-profiles", "position_guidance"],
    queryFn: () => api.strategyProfiles("position_guidance"),
  });
  const defaultProfile = positionProfiles?.find((p) => p.is_default) ?? positionProfiles?.[0] ?? null;
  const activeProfileId = selectedProfileId ?? defaultProfile?.id ?? null;

  const { data: positions, isLoading: positionsLoading } = useQuery({
    queryKey: ["positions"],
    queryFn: api.positions,
  });

  const { data: positionSignals } = useQuery({
    queryKey: ["position-signals"],
    queryFn: () => api.positionSignals(),
  });

  const activePositions = positions?.filter((p) => (p.quantity ?? 0) > 0) ?? [];

  const stats = useMemo(() => {
    const rows = positionSignals ?? [];
    return {
      total: rows.length,
      actionAlerts: rows.filter((row) => ["TRIM_PROFIT", "ENTER_TAIL_MODE", "TRIM_TAIL", "EXIT_TAIL", "REVIEW_POSITION", "STOP_ADDING", "REDUCE_RISK", "EXIT_POSITION"].includes(row.signal)).length,
      tailMode: rows.filter((row) => row.tail_mode).length,
      dataIssues: rows.filter((row) => row.signal === "DATA_ERROR").length,
    };
  }, [positionSignals]);

  const alerts = useMemo(
    () => (positionSignals ?? []).filter((row) => ["TRIM_PROFIT", "ENTER_TAIL_MODE", "TRIM_TAIL", "EXIT_TAIL", "REVIEW_POSITION", "STOP_ADDING", "REDUCE_RISK", "EXIT_POSITION"].includes(row.signal)),
    [positionSignals]
  );
  const holdPositions = useMemo(() => (positionSignals ?? []).filter((row) => row.signal === "HOLD"), [positionSignals]);
  const dataIssues = useMemo(() => (positionSignals ?? []).filter((row) => row.signal === "DATA_ERROR"), [positionSignals]);
  const hasRun = (positionSignals?.length ?? 0) > 0;

  const onRun = async () => {
    setRunMessage(null);
    setRunError(null);
    try {
      const result = await api.runPositionSignals(activeProfileId ?? undefined);
      if (result.status === "FAILED") {
        setRunError(result.error ?? "Position guidance run failed");
        return;
      }
      setRunMessage(`Run completed: ${result.signals_generated} signals, ${result.data_error_count} data errors`);
      await queryClient.invalidateQueries({ queryKey: ["position-signals"] });
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "Network error");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-text-primary">Portfolio</h2>
        <p className="text-sm text-text-muted mt-1">
          Current holdings and position management signals.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <TabButton active={activeTab === "holdings"} onClick={() => setActiveTab("holdings")}>Holdings</TabButton>
        <TabButton active={activeTab === "management"} onClick={() => setActiveTab("management")}>Position Management</TabButton>
      </div>

      {activeTab === "holdings" ? (
        <GlassyCard title="Current Holdings">
          {positionsLoading ? (
            <div className="h-40 bg-surface-hover animate-pulse rounded-xl" />
          ) : activePositions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="tableHeader">
                    <th className="text-left py-3 pr-4">Symbol</th>
                    <th className="text-left py-3 pr-4">Status</th>
                    <th className="text-right py-3 pr-4">Qty</th>
                    <th className="text-right py-3 pr-4">Avg Cost</th>
                    <th className="text-right py-3 pr-4">Last Price</th>
                    <th className="text-right py-3 pr-4">Unrealized P&amp;L</th>
                    <th className="text-right py-3 pr-4">Day P&amp;L</th>
                    <th className="text-right py-3 pr-4">Stop</th>
                    <th className="text-right py-3 pr-4">Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {activePositions.map((pos) => {
                    const weight = pos.position_pct ?? 0;
                    return (
                      <tr className="tableRow">
                        <td className="py-3 pr-4 font-mono font-bold text-text-primary">{pos.symbol}</td>
                        <td className="tableCellStatus"><PositionChip unrealizedPnl={pos.unrealized_pnl} weight={weight} /></td>
                        <td className="tableCellNumeric">{formatQuantity(pos.quantity)}</td>
                        <td className="tableCellNumeric"><PriceDisplay value={pos.avg_cost} prefix="$" /></td>
                        <td className="tableCellNumeric"><PriceDisplay value={pos.current_price} prefix="$" /></td>
                        <td className={`tableCellNumeric ${(pos.unrealized_pnl ?? 0) >= 0 ? "value-up" : "value-down"}`}>
                          <PriceDisplay value={pos.unrealized_pnl} prefix="$" colorize />
                        </td>
                        <td className={`tableCellNumeric ${(pos.day_pnl ?? 0) >= 0 ? "value-up" : "value-down"}`}>
                          <PriceDisplay value={pos.day_pnl} prefix="$" colorize />
                        </td>
                        <td className="tableCellNumeric text-accent-red"><PriceDisplay value={pos.stop_level} prefix="$" /></td>
                        <td className="tableCellNumeric text-text-secondary">{formatPercent(pos.position_pct)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-text-muted text-sm">No open holdings</p>
            </div>
          )}
        </GlassyCard>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="text-xl font-semibold text-text-primary">Position Management</h3>
              <p className="text-sm text-text-muted mt-1">
                Guidance only. No trades are placed.
              </p>
            </div>
            <div className="flex flex-col items-end gap-2">
              {positionProfiles && positionProfiles.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-text-muted uppercase tracking-wider">Guidance Strategy:</span>
                  <div className="relative">
                    <select
                      value={activeProfileId ?? ""}
                      onChange={(e) => setSelectedProfileId(e.target.value || null)}
                      className="appearance-none px-3 py-2 pr-8 rounded-xl bg-surface border border-surface-border
                                 text-sm font-medium text-text-primary cursor-pointer
                                 focus:outline-none focus:border-accent-blue"
                    >
                      {positionProfiles.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                      <svg className="w-4 h-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      const prof = positionProfiles.find((p) => p.id === activeProfileId);
                      if (prof) setRulesProfile(prof);
                    }}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl
                               bg-surface-hover border border-surface-border
                               text-text-muted text-sm font-medium
                               hover:text-text-primary transition-colors"
                    title="View strategy rules"
                  >
                    <BookOpen size={14} />
                    View Rules
                  </button>
                </div>
              )}
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-text-muted uppercase tracking-wider">Actions:</span>
                <button
                  onClick={onRun}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-purple/10 text-accent-purple border border-accent-purple/25 font-medium hover:bg-accent-purple/15 transition-colors"
                >
                  <RotateCcw size={16} />
                  Refresh Position Guidance
                </button>
              </div>
            </div>
          </div>

          <div className="mb-1 px-4 py-3 rounded-xl border border-accent-amber/25 bg-accent-amber/10 text-sm text-accent-amber flex items-center gap-2">
            <AlertTriangle size={16} />
            Guidance only. No trades are placed. Manage orders manually in moomoo.
          </div>

          {runMessage && <div className="text-sm text-text-secondary font-mono">{runMessage}</div>}
          {runError && (
            <div className="px-4 py-3 rounded-xl border border-accent-red/25 bg-accent-red/10 text-sm text-accent-red flex items-center gap-2">
              <AlertTriangle size={16} />
              <span className="flex-1">{runError}</span>
              <button onClick={() => setRunError(null)} className="text-accent-red/60 hover:text-accent-red text-xs font-medium">Dismiss</button>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <GlassyCard><div className="flex items-center justify-between"><div><p className="text-[11px] uppercase tracking-wider text-text-muted mb-1">Positions Checked</p><p className="text-2xl font-semibold font-mono text-text-primary">{stats.total}</p></div><Shield size={20} className="text-accent-blue/40" /></div></GlassyCard>
            <GlassyCard><div className="flex items-center justify-between"><div><p className="text-[11px] uppercase tracking-wider text-text-muted mb-1">Action Alerts</p><p className="text-2xl font-semibold font-mono text-text-primary">{stats.actionAlerts}</p></div><Sparkles size={20} className="text-accent-purple/40" /></div></GlassyCard>
            <GlassyCard><div className="flex items-center justify-between"><div><p className="text-[11px] uppercase tracking-wider text-text-muted mb-1">Tail Positions</p><p className="text-2xl font-semibold font-mono text-text-primary">{stats.tailMode}</p></div><Shield size={20} className="text-accent-purple/40" /></div></GlassyCard>
            <GlassyCard><div className="flex items-center justify-between"><div><p className="text-[11px] uppercase tracking-wider text-text-muted mb-1">Data Issues</p><p className="text-2xl font-semibold font-mono text-text-primary">{stats.dataIssues}</p></div><AlertTriangle size={20} className="text-accent-red/40" /></div></GlassyCard>
          </div>

          <SignalSection
            title="Action Alerts"
            rows={alerts}
            emptyText={hasRun ? "No active action alerts. All evaluated holdings are currently HOLD." : "Run Position Guidance to evaluate your holdings."}
          />

          <SignalSection
            title="Hold Positions"
            rows={holdPositions}
            emptyText={hasRun ? "No HOLD positions." : "Run Position Guidance to populate hold positions."}
          />

          <SignalSection
            title="Data Issues"
            rows={dataIssues}
            emptyText={hasRun ? "No data issues." : "Run Position Guidance to check for data issues."}
          />
        </div>
      )}

      {rulesProfile && (
        <StrategyRulesModal profile={rulesProfile} onClose={() => setRulesProfile(null)} />
      )}
    </div>
  );
}
