"use client";

import { X } from "lucide-react";
import type { StrategyProfileResponse } from "@/lib/types";

function formatPct(value: number | undefined | null, alwaysSign = false): string {
  if (value == null) return "--";
  const sign = alwaysSign && value > 0 ? "+" : "";
  return `${sign}${value}%`;
}

function EntryRulesView({ profile }: { profile: StrategyProfileResponse }) {
  const params = profile.parameters ?? {};
  const weights = (params as any).weights ?? {};
  const thresholds = (params as any).buy_score_threshold != null
    ? { buy: (params as any).buy_score_threshold, watch: (params as any).watch_score_threshold }
    : null;
  const benchmark = (params as any).benchmark ?? "SPY";
  const minBars = (params as any).min_bars ?? "--";

  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm text-text-muted mb-0.5">{profile.description}</p>
        <p className="text-xs text-text-muted">Version {profile.version}</p>
      </div>

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
          Scoring Weights
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
                  style={{ width: `${(val as number)}%` }}
                />
              </div>
              <span className="text-sm font-mono text-text-primary w-8 text-right">
                {val as number}
              </span>
            </div>
          ))}
        </div>
      </div>

      {thresholds && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
            Signal Thresholds
          </h4>
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-lg bg-accent-green/10 border border-accent-green/20">
              <p className="text-xs text-text-muted mb-1">Buy Candidate</p>
              <p className="text-lg font-mono text-accent-green font-bold">
                Score &ge; {thresholds.buy}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-accent-amber/10 border border-accent-amber/20">
              <p className="text-xs text-text-muted mb-1">Watchlist</p>
              <p className="text-lg font-mono text-accent-amber font-bold">
                Score &ge; {thresholds.watch}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-accent-red/10 border border-accent-red/20">
              <p className="text-xs text-text-muted mb-1">Avoid / No Setup</p>
              <p className="text-lg font-mono text-accent-red font-bold">
                Score &lt; {thresholds.watch}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 text-sm">
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
