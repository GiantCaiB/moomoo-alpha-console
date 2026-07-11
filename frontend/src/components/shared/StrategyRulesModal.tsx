"use client";

import { X } from "lucide-react";
import type { StrategyProfileResponse } from "@/lib/types";

function formatPct(value: number | undefined | null, alwaysSign = false): string {
  if (value == null) return "--";
  const sign = alwaysSign && value > 0 ? "+" : "";
  return `${sign}${value}%`;
}

function EntryRulesView({ profile }: { profile: StrategyProfileResponse }) {
  const rs = profile.rules_summary as Record<string, any> ?? {};
  const params = profile.parameters ?? {};
  const p = params as any;

  const weights = (rs.scoring_weights ?? p.weights ?? {}) as Record<string, number>;
  const benchmark = rs.benchmark ?? p.benchmark ?? "SPY";
  const minBars = rs.min_bars ?? p.min_bars ?? "--";

  const buyThreshold = p.buy_score_threshold ?? 75;
  const watchThreshold = p.watch_score_threshold ?? 65;
  const maxSma20Dist = p.entry_filters?.max_distance_above_sma20_pct ?? 15;
  const minVolRatio = p.entry_filters?.min_volume_ratio ?? 0.5;
  const rs20dMargin = p.relative_strength_filters?.underperform_spy_20d_hard_fail_margin_pct ?? 3;
  const rs60dMargin = p.relative_strength_filters?.underperform_spy_60d_hard_fail_margin_pct ?? 5;

  const thresholds = rs.thresholds ?? { buy: buyThreshold, watch: watchThreshold };
  const entryFilters = rs.entry_filters ?? p.entry_filters ?? {};
  const rsFilters = rs.relative_strength_filters ?? {};

  const buyCriteria: string[] = rs.buy_criteria?.length
    ? rs.buy_criteria
    : [
        `Score \u2265 ${buyThreshold}`,
        "Price above SMA50",
        "Price above SMA200",
        `Price not more than ${maxSma20Dist}% above SMA20`,
        `Volume \u2265 ${minVolRatio}x 20-day average`,
        `20d return does not underperform ${benchmark} by more than ${rs20dMargin}%`,
        `60d return does not underperform ${benchmark} by more than ${rs60dMargin}%`,
        "No data quality issues",
      ];

  const watchlistCriteria: string[] = rs.watchlist_criteria?.length
    ? rs.watchlist_criteria
    : [
        `Score \u2265 ${watchThreshold}`,
        "No major hard filter failures",
        "Minor warnings allowed:",
        `  slight underperformance vs ${benchmark}`,
        "  borderline volume",
        "  slightly extended price",
      ];

  const avoidCriteria: string[] = rs.avoid_criteria?.length
    ? rs.avoid_criteria
    : [
        `Score < ${watchThreshold}`,
        "Price below SMA50",
        "Price below SMA200",
        `Price more than ${maxSma20Dist}% above SMA20`,
        `Volume < ${minVolRatio}x 20-day average`,
        `20d return underperforms ${benchmark} by more than ${rs20dMargin}%`,
        `60d return underperforms ${benchmark} by more than ${rs60dMargin}%`,
      ];

  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm text-text-muted mb-0.5">{profile.description}</p>
        <p className="text-xs text-text-muted">Version {profile.version}</p>
      </div>

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
          Scoring Model
        </h4>
        <div className="space-y-1">
          {Object.entries(weights).map(([key, val]) => (
            <div key={key} className="flex items-center gap-3">
              <span className="text-sm text-text-secondary w-40 capitalize">
                {key.replace(/_/g, " ")}
              </span>
              <div className="flex-1 h-2 rounded-full bg-surface-border overflow-hidden">
                <div
                  className="h-full rounded-full bg-accent-blue"
                  style={{ width: `${val}%` }}
                />
              </div>
              <span className="text-sm font-mono text-text-primary w-8 text-right">
                {val}
              </span>
            </div>
          ))}
        </div>
        <p className="text-xs text-text-muted mt-1">
          Total: {Object.values(weights).reduce((a: number, b: number) => a + b, 0)} / 100
        </p>
      </div>

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
          Buy Candidate Criteria
        </h4>
        <div className="p-3 rounded-lg bg-accent-green/10 border border-accent-green/20">
          <ul className="space-y-1">
            {buyCriteria.map((c: string, i: number) => (
              <li key={i} className="text-sm text-text-primary flex items-start gap-2">
                <span className="text-accent-green mt-0.5 shrink-0">&#10003;</span>
                <span>{c.startsWith("  ") ? c.trim() : c}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
          Watchlist Criteria
        </h4>
        <div className="p-3 rounded-lg bg-accent-amber/10 border border-accent-amber/20">
          <ul className="space-y-1">
            {watchlistCriteria.map((c: string, i: number) => {
              const isIndent = c.startsWith("  ");
              return (
                <li key={i} className={`text-sm flex items-start gap-2 ${isIndent ? "text-text-secondary ml-4" : "text-text-primary"}`}>
                  <span className="text-accent-amber mt-0.5 shrink-0">{isIndent ? "\u2022" : "\u26A0"}</span>
                  <span>{isIndent ? c.trim() : c}</span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
          Avoid / Hard Fails
        </h4>
        <div className="p-3 rounded-lg bg-accent-red/10 border border-accent-red/20">
          <ul className="space-y-1">
            {avoidCriteria.map((c: string, i: number) => (
              <li key={i} className="text-sm text-text-primary flex items-start gap-2">
                <span className="text-accent-red mt-0.5 shrink-0">&#10007;</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
          Key Parameters
        </h4>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="p-3 rounded-lg bg-surface-hover">
            <span className="text-text-muted">Buy Threshold</span>
            <p className="font-mono font-bold text-accent-green">
              Score &ge; {thresholds?.buy ?? "--"}
            </p>
          </div>
          <div className="p-3 rounded-lg bg-surface-hover">
            <span className="text-text-muted">Watch Threshold</span>
            <p className="font-mono font-bold text-accent-amber">
              Score &ge; {thresholds?.watch ?? "--"}
            </p>
          </div>
          <div className="p-3 rounded-lg bg-surface-hover">
            <span className="text-text-muted">Max SMA20 Distance</span>
            <p className="font-mono font-bold text-text-primary">
              {entryFilters.max_distance_above_sma20_pct ?? maxSma20Dist}%
            </p>
          </div>
          <div className="p-3 rounded-lg bg-surface-hover">
            <span className="text-text-muted">Min Volume Ratio</span>
            <p className="font-mono font-bold text-text-primary">
              {entryFilters.min_volume_ratio ?? minVolRatio}x
            </p>
          </div>
          <div className="p-3 rounded-lg bg-surface-hover">
            <span className="text-text-muted">RS 20d Hard Fail Margin</span>
            <p className="font-mono font-bold text-text-primary">
              &gt; {rsFilters.hard_fail_margins?.["20d"] ?? rs20dMargin}%
            </p>
          </div>
          <div className="p-3 rounded-lg bg-surface-hover">
            <span className="text-text-muted">RS 60d Hard Fail Margin</span>
            <p className="font-mono font-bold text-text-primary">
              &gt; {rsFilters.hard_fail_margins?.["60d"] ?? rs60dMargin}%
            </p>
          </div>
          <div className="p-3 rounded-lg bg-surface-hover">
            <span className="text-text-muted">Benchmark</span>
            <p className="font-mono font-bold text-text-primary">{benchmark}</p>
          </div>
          <div className="p-3 rounded-lg bg-surface-hover">
            <span className="text-text-muted">Min History</span>
            <p className="font-mono font-bold text-text-primary">{minBars} bars</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function PositionRulesView({ profile }: { profile: StrategyProfileResponse }) {
  const params = profile.parameters ?? {};
  const p = params as any;
  const trimThresholds: Array<{ gain_pct: number; trim_pct: number }> = p.trim_thresholds ?? [];
  const tailThreshold = p.tail_threshold_pct ?? 100;
  const ld = p.loss_defense ?? {};
  const tailExit = p.tail_exit ?? {};

  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm text-text-muted mb-0.5">{profile.description}</p>
        <p className="text-xs text-text-muted">Version {profile.version}</p>
      </div>

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
          Threshold Timeline
        </h4>
        <div className="space-y-1">
          <div className="flex items-center gap-3 p-2 rounded bg-accent-red/10 border border-accent-red/20">
            <span className="text-xs font-mono text-accent-red font-bold w-16 text-right">
              {formatPct(ld.exit_review_pct)}
            </span>
            <span className="text-sm text-text-primary">Exit Review</span>
            <span className="text-xs text-text-muted ml-auto">
              Major risk threshold breached
            </span>
          </div>
          <div className="flex items-center gap-3 p-2 rounded bg-accent-red/5 border border-accent-red/10">
            <span className="text-xs font-mono text-accent-red font-bold w-16 text-right">
              {formatPct(ld.reduce_risk_pct)}
            </span>
            <span className="text-sm text-text-primary">Reduce Risk</span>
            <span className="text-xs text-text-muted ml-auto">
              Reduce exposure manually
            </span>
          </div>
          <div className="flex items-center gap-3 p-2 rounded bg-accent-amber/10 border border-accent-amber/20">
            <span className="text-xs font-mono text-accent-amber font-bold w-16 text-right">
              {formatPct(ld.stop_adding_pct)}
            </span>
            <span className="text-sm text-text-primary">Stop Adding</span>
            <span className="text-xs text-text-muted ml-auto">
              Do not add until trend improves
            </span>
          </div>
          <div className="flex items-center gap-3 p-2 rounded bg-accent-amber/5 border border-accent-amber/10">
            <span className="text-xs font-mono text-accent-amber font-bold w-16 text-right">
              {formatPct(ld.review_pct)}
            </span>
            <span className="text-sm text-text-primary">Review</span>
            <span className="text-xs text-text-muted ml-auto">
              Review thesis and risk
            </span>
          </div>
          <div className="border-t border-surface-border/50 my-1" />
          {trimThresholds.map((t: any, i: number) => (
            <div key={i} className="flex items-center gap-3 p-2 rounded bg-accent-green/10 border border-accent-green/20">
              <span className="text-xs font-mono text-accent-green font-bold w-16 text-right">
                {formatPct(t.gain_pct, true)}
              </span>
              <span className="text-sm text-text-primary">Trim {t.trim_pct}%</span>
              <span className="text-xs text-text-muted ml-auto">
                Take partial profit
              </span>
            </div>
          ))}
          <div className="flex items-center gap-3 p-2 rounded bg-accent-purple/10 border border-accent-purple/20">
            <span className="text-xs font-mono text-accent-purple font-bold w-16 text-right">
              {formatPct(tailThreshold, true)}
            </span>
            <span className="text-sm text-text-primary">Enter Tail Mode</span>
            <span className="text-xs text-text-muted ml-auto">
              Recover cost basis, keep profit tail
            </span>
          </div>
        </div>
      </div>

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
          Tail Exit Rules
        </h4>
        <div className="space-y-1 text-sm">
          <div className="flex items-center justify-between p-2 rounded bg-surface-hover">
            <span className="text-text-secondary">Drawdown exit</span>
            <span className="font-mono text-accent-red">
              &ge; {tailExit.drawdown_exit_pct ?? 35}%
            </span>
          </div>
          <div className="flex items-center justify-between p-2 rounded bg-surface-hover">
            <span className="text-text-secondary">Weekly close below SMA{tailExit.weekly_sma_trim ?? 20}</span>
            <span className="font-mono text-accent-amber">Trim Tail</span>
          </div>
          <div className="flex items-center justify-between p-2 rounded bg-surface-hover">
            <span className="text-text-secondary">Weekly close below SMA{tailExit.weekly_sma_exit ?? 30}</span>
            <span className="font-mono text-accent-red">Exit Tail</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function StrategyRulesModal({
  profile,
  onClose,
}: {
  profile: StrategyProfileResponse;
  onClose: () => void;
}) {
  const isEntry = profile.strategy_type === "entry";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-xl max-h-[85vh] overflow-y-auto mx-4 rounded-2xl bg-surface border border-surface-border shadow-2xl">
        <div className="sticky top-0 bg-surface z-10 flex items-center justify-between px-6 py-4 border-b border-surface-border">
          <div>
            <h3 className="text-lg font-semibold text-text-primary">{profile.name}</h3>
            <p className="text-xs text-text-muted capitalize">{profile.strategy_type.replace(/_/g, " ")}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-surface-hover text-text-muted hover:text-text-primary transition-colors"
          >
            <X size={18} />
          </button>
        </div>
        <div className="px-6 py-5">
          {isEntry ? <EntryRulesView profile={profile} /> : <PositionRulesView profile={profile} />}
        </div>
      </div>
    </div>
  );
}
