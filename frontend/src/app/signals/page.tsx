"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import GlassyCard from "@/components/shared/GlassyCard";
import PriceDisplay from "@/components/shared/PriceDisplay";
import StatusBadge from "@/components/shared/StatusBadge";
import { useState } from "react";
import { Play, CheckCircle, XCircle, Info } from "lucide-react";

export default function SignalsPage() {
  const queryClient = useQueryClient();
  const [selectedSignal, setSelectedSignal] = useState<string | null>(null);

  const { data: signals, isLoading } = useQuery({
    queryKey: ["signals"],
    queryFn: api.signals,
    refetchInterval: 30000,
  });

  const runMutation = useMutation({
    mutationFn: api.runSignals,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["signals"] });
    },
  });

  const buySignals = signals?.filter((s) => s.verdict === "BUY_STARTER") || [];
  const watchSignals = signals?.filter((s) => s.verdict === "WATCH") || [];
  const avoidSignals = signals?.filter((s) => s.verdict === "AVOID") || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-text-primary">Signals</h2>
          <p className="text-sm text-text-muted mt-1">
            Momentum Relative Strength Screener
          </p>
        </div>
        <button
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-green/10
                     border border-accent-green/30 text-accent-green text-sm font-medium
                     hover:bg-accent-green/20 transition-colors disabled:opacity-50"
        >
          <Play size={16} />
          {runMutation.isPending ? "Running..." : "Run Screener"}
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 bg-surface-hover animate-pulse rounded-xl"
            />
          ))}
        </div>
      ) : signals && signals.length > 0 ? (
        <div className="space-y-4">
          <GlassyCard title="BUY Signals">
            {buySignals.length === 0 ? (
              <p className="text-sm text-text-muted text-center py-4">
                No BUY signals. Run the screener.
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
                  />
                ))}
              </div>
            )}
          </GlassyCard>

          <GlassyCard title="Watch List">
            {watchSignals.length === 0 ? (
              <p className="text-sm text-text-muted text-center py-4">
                No WATCH signals
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
                  />
                ))}
              </div>
            )}
          </GlassyCard>

          <GlassyCard title="Avoid / No Signal">
            {avoidSignals.length === 0 ? (
              <p className="text-sm text-text-muted text-center py-4">
                No AVOID signals
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
              No signals yet. Run the screener to generate trading candidates.
            </p>
            <button
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending}
              className="px-6 py-2.5 rounded-lg bg-accent-green/10 border border-accent-green/30
                         text-accent-green text-sm font-medium hover:bg-accent-green/20
                         transition-colors disabled:opacity-50"
            >
              {runMutation.isPending ? "Running..." : "Run Screener Now"}
            </button>
          </div>
        </GlassyCard>
      )}
    </div>
  );
}

function SignalRow({
  sig,
  isSelected,
  onToggle,
}: {
  sig: any;
  isSelected: boolean;
  onToggle: () => void;
}) {
  return (
    <div>
      <div
        className="flex items-center justify-between py-2.5 px-3 rounded-lg
                   bg-surface-hover/30 hover:bg-surface-hover/50 cursor-pointer
                   transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <span className="font-mono font-bold text-text-primary text-sm">
            {sig.symbol}
          </span>
          <StatusBadge status={sig.verdict} />
          <div className="flex items-center gap-1">
            {(sig.scores || []).map((s: any) => (
              <div
                key={s.category}
                className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-hover"
                title={`${s.category}: ${s.score}/${s.max_score}`}
              >
                <span className="text-[10px] text-text-muted">{s.category.slice(0, 3)}</span>
                <span className="text-[10px] font-mono text-accent-green">
                  {s.score}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono text-text-secondary">
          <span>
            Score:{" "}
            <span className="text-accent-green font-bold">
              {sig.total_score}
            </span>
          </span>
          <Info size={14} className="text-text-muted" />
        </div>
      </div>

      {isSelected && (
        <div className="mx-3 mb-2 p-4 rounded-lg bg-surface-hover/50 border border-surface-border/50">
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

          {sig.scores && (
            <div className="mb-4">
              <p className="text-xs text-text-muted mb-2">Score Breakdown</p>
              <div className="space-y-1">
                {sig.scores.map((s: any) => {
                  const pct = (s.score / s.max_score) * 100;
                  return (
                    <div key={s.category} className="flex items-center gap-2">
                      <span className="text-xs text-text-secondary w-32">
                        {s.category}
                      </span>
                      <div className="flex-1 h-2 rounded-full bg-surface-border overflow-hidden">
                        <div
                          className="h-full rounded-full bg-accent-green transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono text-text-secondary w-16 text-right">
                        {s.score}/{s.max_score}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <p className="text-xs text-text-muted mb-1">Reason</p>
          <p className="text-sm text-text-primary mb-3">{sig.reason}</p>

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
