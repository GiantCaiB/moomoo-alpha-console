"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { isReadOnlyMode } from "@/lib/readonly";
import { useBrokerHealth } from "@/app/providers";
import { getSourceBadge } from "@/lib/source_badge";
import GlassyCard from "@/components/shared/GlassyCard";
import PriceDisplay from "@/components/shared/PriceDisplay";
import StatusBadge from "@/components/shared/StatusBadge";
import { useState, useMemo } from "react";
import { Play, Info, ShieldBan, AlertTriangle, Trash2, BookOpen } from "lucide-react";
import StrategyRulesModal from "@/components/shared/StrategyRulesModal";
import type { StrategyProfileResponse, PriceFreshnessInfo } from "@/lib/types";

export default function SignalsPage() {
  const queryClient = useQueryClient();
  const [selectedSignal, setSelectedSignal] = useState<string | null>(null);
  const [runFeedback, setRunFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [rulesProfile, setRulesProfile] = useState<StrategyProfileResponse | null>(null);
  const { health } = useBrokerHealth();
  const readOnly = isReadOnlyMode(health);
  const isMoomoo = health?.account_environment?.startsWith("moomoo") ?? false;

  const { data: universe } = useQuery({
    queryKey: ["trading-universe"],
    queryFn: api.tradingUniverse,
  });
  const universeSymbols = universe?.symbols ?? [];

  const { data: entryProfiles } = useQuery({
    queryKey: ["strategy-profiles", "entry"],
    queryFn: () => api.strategyProfiles("entry"),
  });

  const { data: signals, isLoading } = useQuery({
    queryKey: ["signals"],
    queryFn: () => api.signals(),
    refetchInterval: 30000,
  });

  const { data: staleSummary } = useQuery({
    queryKey: ["signals", "stale-count"],
    queryFn: api.staleSignalCount,
    enabled: isMoomoo,
    refetchInterval: 30000,
  });

  const { data: priceFreshness } = useQuery({
    queryKey: ["signals", "current-prices", signals?.map((s) => s.symbol).join(",")],
    queryFn: () => {
      const symbols = signals?.map((s) => s.symbol) ?? [];
      const unique = [...new Set(symbols)];
      return unique.length > 0 ? api.currentPrices(unique) : { prices: {} };
    },
    enabled: (signals?.length ?? 0) > 0,
    refetchInterval: 60000,
  });

  const freshnessMap = useMemo(() => {
    if (!priceFreshness?.prices) return {};
    return priceFreshness.prices as Record<string, PriceFreshnessInfo>;
  }, [priceFreshness]);

  const defaultProfile = entryProfiles?.find((p) => p.is_default) ?? entryProfiles?.[0] ?? null;
  const activeProfileId = selectedProfileId ?? defaultProfile?.id ?? null;

  const runMutation = useMutation({
    mutationFn: () => api.runSignals(activeProfileId ?? undefined),
    onMutate: () => setRunFeedback(null),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["signals"] });
      queryClient.invalidateQueries({ queryKey: ["signals", "stale-count"] });
      const parts: string[] = [];
      parts.push(`Status: ${result.status}`);
      if (result.signals_generated !== undefined) {
        parts.push(`Signals: ${result.signals_generated}`);
      }
      if (result.data_error_count !== undefined && result.data_error_count > 0) {
        parts.push(`Errors: ${result.data_error_count}`);
      }
      if (result.error) {
        parts.push(`Detail: ${result.error}`);
      }
      setRunFeedback({ type: "success", message: parts.join(" | ") });
    },
    onError: (err: Error) => {
      setRunFeedback({ type: "error", message: err.message });
    },
  });

  const deleteStaleMutation = useMutation({
    mutationFn: api.deleteStaleSignals,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["signals"] });
      queryClient.invalidateQueries({ queryKey: ["signals", "stale-count"] });
    },
  });

  const filteredSignals = useMemo(() => {
    if (!isMoomoo || !signals) return signals;
    return signals.filter(
      (s) =>
        (s.data_source === "moomoo" || s.data_source === "moomoo_snapshot_plus_yfinance_kline") &&
        s.is_real_market_data === true &&
        universeSymbols.includes(s.symbol)
    );
  }, [isMoomoo, signals, universeSymbols]);

  const buySignals = filteredSignals?.filter((s) => s.verdict === "BUY_STARTER" && s.data_quality_status === "OK") || [];
  const watchSignals = filteredSignals?.filter((s) => s.verdict === "WATCH" && s.data_quality_status === "OK") || [];
  const avoidSignals = filteredSignals?.filter((s) => s.verdict === "AVOID" && s.data_quality_status === "OK") || [];
  const dataIssueSignals = filteredSignals?.filter((s) => s.data_quality_status !== "OK") || [];
  const hasStale = (staleSummary?.stale_count ?? 0) > 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold text-text-primary">Entry Signals</h2>
          <p className="text-sm text-text-muted mt-1">
            Momentum and relative strength ideas for new positions.
          </p>
          <p className="text-xs text-text-muted mt-1">
            Entry Signals evaluate new position ideas. Existing holdings are managed under Portfolio → Position Management.
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          {entryProfiles && entryProfiles.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-text-muted uppercase tracking-wider">Strategy:</span>
              <div className="relative">
                <select
                  value={activeProfileId ?? ""}
                  onChange={(e) => setSelectedProfileId(e.target.value || null)}
                  className="appearance-none px-3 py-2 pr-8 rounded-xl bg-surface border border-surface-border
                             text-sm font-medium text-text-primary cursor-pointer
                             focus:outline-none focus:border-accent-blue"
                >
                  {entryProfiles.map((p) => (
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
                  const prof = entryProfiles.find((p) => p.id === activeProfileId);
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
            {hasStale && (
              <button
                onClick={() => deleteStaleMutation.mutate()}
                disabled={deleteStaleMutation.isPending}
                className="flex items-center gap-2 px-3 py-2 rounded-xl bg-accent-amber/10
                           border border-accent-amber/25 text-accent-amber text-sm font-medium
                           hover:bg-accent-amber/15 transition-colors disabled:opacity-50"
              >
                <Trash2 size={16} />
                {deleteStaleMutation.isPending ? "Clearing..." : "Clear Stale"}
              </button>
            )}
            <button
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-green/10
                         border border-accent-green/25 text-accent-green text-sm font-medium
                         hover:bg-accent-green/15 transition-colors disabled:opacity-50"
            >
              <Play size={16} />
              {runMutation.isPending ? "Running..." : "Run Entry Screener"}
            </button>
          </div>
        </div>
      </div>

      {readOnly && (
        <div className="mb-4 px-4 py-2 rounded-lg bg-accent-amber/10 border border-accent-amber/30 text-accent-amber text-sm flex items-center gap-2">
          <ShieldBan size={16} />
          Signals are research only. Order approval is disabled in read-only mode.
        </div>
      )}

      {hasStale && (
        <div className="mb-4 px-4 py-2 rounded-lg bg-accent-amber/10 border border-accent-amber/30 text-accent-amber text-sm flex items-center gap-2">
          <AlertTriangle size={16} />
          {(() => {
            const staleCount = staleSummary?.stale_count ?? 0;
            const localCount = staleSummary?.local_or_mock_count ?? 0;
            const universeCount = staleSummary?.out_of_universe_count ?? 0;
            const universeSymbols = staleSummary?.out_of_universe_symbols ?? [];
            if (localCount > 0 && universeCount === 0) {
              return `${staleCount} stale signal${staleCount !== 1 ? "s" : ""} hidden.`;
            }
            if (universeCount > 0 && localCount === 0) {
              return `${staleCount} signal${staleCount !== 1 ? "s" : ""} outside current Trading Universe hidden: ${universeSymbols.join(", ")}.`;
            }
            return `${staleCount} stale signal${staleCount !== 1 ? "s" : ""} hidden: local/mock and outside current Trading Universe.`;
          })()}{" "}
          <button
            onClick={() => deleteStaleMutation.mutate()}
            className="underline font-medium hover:no-underline"
          >
            Clear Stale
          </button>
        </div>
      )}

      {runFeedback && (
        <div
          className={`mb-4 px-4 py-2 rounded-lg text-sm flex items-center gap-2 ${
            runFeedback.type === "error"
              ? "bg-accent-red/10 border border-accent-red/30 text-accent-red"
              : "bg-accent-green/10 border border-accent-green/30 text-accent-green"
          }`}
        >
          {runFeedback.type === "error" ? <ShieldBan size={16} /> : <Info size={16} />}
          <span className="flex-1">{runFeedback.message}</span>
          <button
            onClick={() => setRunFeedback(null)}
            className="text-xs underline hover:no-underline opacity-70 hover:opacity-100"
          >
            Dismiss
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 bg-surface-hover animate-pulse rounded-xl"
            />
          ))}
        </div>
      ) : filteredSignals && filteredSignals.length > 0 ? (
        <div className="space-y-4">
          <GlassyCard title="Buy Candidates">
            {buySignals.length === 0 ? (
              <p className="text-sm text-text-muted text-center py-4">
                No buy candidates right now. Refresh the screener when ready.
              </p>
            ) : (
              <div className="space-y-2">
                  {buySignals.map((sig) => (
                    <SignalRow
                      key={sig.id}
                      sig={sig}
                      isSelected={selectedSignal === sig.id}
                      onToggle={() =>
                        setSelectedSignal(
                          selectedSignal === sig.id ? null : sig.id
                        )
                      }
                      freshnessInfo={freshnessMap[sig.symbol]}
                    />
                  ))}
              </div>
            )}
          </GlassyCard>

          <GlassyCard title="Watchlist Candidates">
            {watchSignals.length === 0 ? (
              <p className="text-sm text-text-muted text-center py-4">
                No watchlist candidates
              </p>
            ) : (
              <div className="space-y-2">
                  {watchSignals.map((sig) => (
                    <SignalRow
                      key={sig.id}
                      sig={sig}
                      isSelected={selectedSignal === sig.id}
                      onToggle={() =>
                        setSelectedSignal(
                          selectedSignal === sig.id ? null : sig.id
                        )
                      }
                      freshnessInfo={freshnessMap[sig.symbol]}
                    />
                  ))}
              </div>
            )}
          </GlassyCard>

          <GlassyCard title="Avoid / No Setup">
            {avoidSignals.length === 0 ? (
              <p className="text-sm text-text-muted text-center py-4">
                No avoid rows
              </p>
            ) : (
              <div className="space-y-2">
                  {avoidSignals.map((sig) => (
                    <SignalRow
                      key={sig.id}
                      sig={sig}
                      isSelected={selectedSignal === sig.id}
                      onToggle={() =>
                        setSelectedSignal(
                          selectedSignal === sig.id ? null : sig.id
                        )
                      }
                      freshnessInfo={freshnessMap[sig.symbol]}
                    />
                  ))}
              </div>
            )}
          </GlassyCard>

          <GlassyCard title="Data Issues">
            {dataIssueSignals.length === 0 ? (
              <p className="text-sm text-text-muted text-center py-4">
                No data issues
              </p>
            ) : (
              <div className="space-y-2">
                  {dataIssueSignals.map((sig) => (
                    <SignalRow
                      key={sig.id}
                      sig={sig}
                      isSelected={selectedSignal === sig.id}
                      onToggle={() =>
                        setSelectedSignal(
                          selectedSignal === sig.id ? null : sig.id
                        )
                      }
                      freshnessInfo={freshnessMap[sig.symbol]}
                    />
                  ))}
              </div>
            )}
          </GlassyCard>
        </div>
      ) : (
        <GlassyCard>
          <div className="text-center py-12">
            <p className="text-text-muted text-sm mb-4">
              No entry alerts right now.
            </p>
            <button
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending}
              className="px-6 py-2.5 rounded-lg bg-accent-green/10 border border-accent-green/30
                         text-accent-green text-sm font-medium hover:bg-accent-green/20
                         transition-colors disabled:opacity-50"
            >
              {runMutation.isPending ? "Running..." : "Run Entry Screener"}
            </button>
          </div>
        </GlassyCard>
      )}

      {rulesProfile && (
        <StrategyRulesModal profile={rulesProfile} onClose={() => setRulesProfile(null)} />
      )}
    </div>
  );
}

function computePriceDeltaPct(signalPrice: number | null, currentPrice: number | null): number | null {
  if (signalPrice == null || currentPrice == null || signalPrice === 0) return null;
  return ((currentPrice - signalPrice) / signalPrice) * 100;
}

function SignalRow({
  sig,
  isSelected,
  onToggle,
  freshnessInfo,
}: {
  sig: any;
  isSelected: boolean;
  onToggle: () => void;
  freshnessInfo?: PriceFreshnessInfo;
}) {
  const badge = getSourceBadge(sig.data_source);
  const reasonLabels: Record<string, string> = {
    Trend: "Trend",
    "Relative Strength": "Relative Strength",
    Volume: "Volume",
    "Volume Confirmation": "Volume",
    "Entry Quality": "Entry",
    "Risk/Reward": "Risk/Reward",
    "Market Regime": "Market",
  };

  const signalPrice = sig.current_price ?? null;
  const currentPrice = freshnessInfo?.current_price ?? null;
  const priceDeltaPct = computePriceDeltaPct(signalPrice, currentPrice);
  const hasPriceMoved =
    priceDeltaPct !== null && Math.abs(priceDeltaPct) > 5;

  return (
    <div className="grid grid-cols-[72px_110px_150px_1fr_120px_32px]">
      <div
        className="contents cursor-pointer"
        onClick={onToggle}
      >
        <span className="font-mono font-bold text-text-primary text-sm py-2.5">
          {sig.symbol}
        </span>
        <span className="py-2.5">
          <StatusBadge status={sig.verdict} />
        </span>
        <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium truncate self-center ${badge.className}`}>
          {badge.label}
        </span>
        <div className="flex items-center gap-1 flex-wrap py-2.5">
          {(sig.scores || []).slice(0, 3).map((s: any) => (
            <div
              key={s.category}
              className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-hover"
              title={`${s.category}: ${s.score}/${s.max_score}`}
            >
              <span className="text-[10px] text-text-muted">{reasonLabels[s.category] ?? s.category}</span>
              <span className="text-[10px] font-mono text-accent-green">
                {Math.round(s.score)}
              </span>
            </div>
          ))}
        </div>
        <div className="text-right font-mono tabular-nums text-xs text-text-secondary self-center py-2.5">
          {sig.data_quality_status === "OK" ? (
            <span>
              Score{" "}
              <span className="text-accent-green font-bold">
                {Math.round(sig.total_score)} / 100
              </span>
            </span>
          ) : (
            <span className="text-accent-red font-bold">Data error</span>
          )}
        </div>
        <div className="self-center justify-self-center py-2.5">
          <Info size={14} className="text-text-muted" />
        </div>
      </div>

      {isSelected && (
        <div className="col-span-full mx-3 mb-2 p-4 rounded-lg bg-surface-hover/50 border border-surface-border/50">
          {!sig.is_real_market_data && (
            <div className="mb-3 flex items-start gap-2 p-2 rounded bg-accent-amber/10 border border-accent-amber/30 text-accent-amber text-xs">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" />
              <div>
                <p className="font-medium">Research signal only</p>
                <p className="mt-0.5">Generated from local/mock data. Not tradeable in read-only mode.</p>
              </div>
            </div>
          )}
          {sig.is_real_market_data && (
            <div className="mb-3 flex items-start gap-2 p-2 rounded bg-accent-blue/10 border border-accent-blue/30 text-accent-blue text-xs">
              <Info size={14} className="mt-0.5 shrink-0" />
              <div>
                <p className="font-medium">Moomoo market data signal</p>
                <p className="mt-0.5">Generated from moomoo quotes and historical kline data. Research only — not tradeable in read-only mode.</p>
              </div>
            </div>
          )}

          {hasPriceMoved && (
            <div className="mb-3 flex items-start gap-2 p-2 rounded bg-accent-amber/10 border border-accent-amber/30 text-accent-amber text-xs">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" />
              <div>
                <p className="font-medium">Price moved significantly since this signal was generated.</p>
                <p className="mt-0.5">Refresh screener before acting.</p>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <p className="text-xs text-text-muted mb-1">Entry Range</p>
              <p className="font-mono text-sm">
                <PriceDisplay value={sig.entry_min} prefix="$" /> -{" "}
                <PriceDisplay value={sig.entry_max} prefix="$" />
              </p>
            </div>
            <div>
              <p className="text-xs text-text-muted mb-1">Stop Level</p>
              <p className="font-mono text-sm text-accent-red">
                <PriceDisplay value={sig.stop_level} prefix="$" />
              </p>
            </div>
            <div>
              <p className="text-xs text-text-muted mb-1">Target Size</p>
              <p className="font-mono text-sm">
                {sig.target_size_pct ?? "--"}%
              </p>
            </div>
            <div>
              <p className="text-xs text-text-muted mb-1">Risk Amount</p>
              <p className="font-mono text-sm">
                <PriceDisplay value={sig.risk_amount} prefix="$" />
              </p>
            </div>
          </div>

          {sig.failed_filters && sig.failed_filters.length > 0 && (
            <div className="mb-4">
              <p className="text-xs text-text-muted mb-2">Failed Filters</p>
              <ul className="list-disc list-inside text-sm text-text-primary space-y-1">
                {sig.failed_filters.map((f: string) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </div>
          )}

          {sig.scores && (
            <div className="mb-4">
              <p className="text-xs text-text-muted mb-2">Score Breakdown</p>
              <div className="space-y-1">
                {sig.scores.map((s: any) => {
                  const pct = s.max_score > 0 ? (s.score / s.max_score) * 100 : 0;
                  return (
                    <div key={s.category} className="flex items-center gap-2">
                      <span className="text-xs text-text-secondary w-32 shrink-0">
                        {reasonLabels[s.category] ?? s.category}
                      </span>
                      <div className="flex-1 h-2 rounded-full bg-surface-border overflow-hidden">
                        <div
                          className="h-full rounded-full bg-accent-green transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono text-text-secondary w-12 text-right shrink-0">
                        {s.score}/{s.max_score}
                      </span>
                      {s.details && (
                        <span className="text-[10px] text-text-muted hidden md:block max-w-[200px] truncate" title={s.details}>
                          {s.details}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3 text-xs">
            <div>
              <p className="text-text-muted mb-0.5">Strategy</p>
              <p className="font-mono text-text-primary">{sig.strategy_name ?? "--"}</p>
            </div>
            <div>
              <p className="text-text-muted mb-0.5">Data Source</p>
              <p className="font-mono text-text-primary">{sig.data_source ?? "--"}</p>
            </div>
            <div>
              <p className="text-text-muted mb-0.5">Price Source</p>
              <p className="font-mono text-text-primary">{sig.price_source ?? "--"}</p>
            </div>
            <div>
              <p className="text-text-muted mb-0.5">Bar Source</p>
              <p className="font-mono text-text-primary">{sig.bar_source ?? "--"}</p>
            </div>
            <div>
              <p className="text-text-muted mb-0.5">Signal Price</p>
              <p className="font-mono text-sm text-text-primary">
                {signalPrice != null ? `$${signalPrice.toFixed(2)}` : "--"}
              </p>
            </div>
            <div>
              <p className="text-text-muted mb-0.5">Current Price</p>
              <p className={`font-mono text-sm ${currentPrice != null ? "text-text-primary" : "text-text-muted"}`}>
                {currentPrice != null ? `$${currentPrice.toFixed(2)}` : "N/A"}
              </p>
            </div>
            <div>
              <p className="text-text-muted mb-0.5">Price Delta</p>
              <p className={`font-mono text-sm ${priceDeltaPct != null ? (priceDeltaPct > 0 ? "text-accent-green" : "text-accent-red") : "text-text-muted"}`}>
                {priceDeltaPct != null
                  ? `${priceDeltaPct > 0 ? "+" : ""}${priceDeltaPct.toFixed(1)}%`
                  : "--"}
              </p>
            </div>
            <div>
              <p className="text-text-muted mb-0.5">Price Timestamp</p>
              <p className="font-mono text-text-primary">
                {sig.price_as_of ?? "-"}
              </p>
            </div>
            <div>
              <p className="text-text-muted mb-0.5">Generated At</p>
              <p className="font-mono text-text-primary">
                {sig.generated_at
                  ? new Date(sig.generated_at).toLocaleString()
                  : "--"}
              </p>
            </div>
            <div>
              <p className="text-text-muted mb-0.5">Real Market Data</p>
              <p className={`font-mono ${sig.is_real_market_data ? "text-accent-green" : "text-accent-amber"}`}>
                {sig.is_real_market_data ? "Yes" : "No"}
              </p>
            </div>
            <div>
              <p className="text-text-muted mb-0.5">Tradeable</p>
              <p className={`font-mono ${sig.is_tradeable ? "text-accent-green" : "text-text-muted"}`}>
                {sig.is_tradeable ? "Yes" : "No"}
              </p>
            </div>
          </div>

          <p className="text-xs text-text-muted mb-1">Reason</p>
          <p className="text-sm text-text-primary mb-3">{sig.reason}</p>

          <div className="mb-3 text-sm text-text-secondary">
            {sig.verdict === "BUY_STARTER" && (
              <p>Starter candidate. Review risk before acting manually.</p>
            )}
            {sig.verdict === "WATCH" && (
              <p>Watch because the setup is constructive but not yet a buy trigger.</p>
            )}
            {sig.verdict === "AVOID" && (
              <p>Avoid because the setup is weak or the momentum filters failed.</p>
            )}
          </div>

          {sig.invalidation && (
            <>
              <p className="text-xs text-text-muted mb-1">Invalidation</p>
              <p className="text-sm text-accent-amber">{sig.invalidation}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
