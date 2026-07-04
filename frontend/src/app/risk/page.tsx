"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatPercent } from "@/lib/format";
import { isReadOnlyMode } from "@/lib/readonly";
import { useBrokerHealth } from "@/app/providers";
import GlassyCard from "@/components/shared/GlassyCard";
import { AlertTriangle, Lock } from "lucide-react";

export default function RiskPage() {
  const queryClient = useQueryClient();

  const { data: risk } = useQuery({
    queryKey: ["risk"],
    queryFn: api.riskStatus,
    refetchInterval: 5000,
  });

  const { health } = useBrokerHealth();
  const readOnly = isReadOnlyMode(health);

  const killSwitchMutation = useMutation({
    mutationFn: api.toggleKillSwitch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["risk"] });
    },
  });

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-text-primary">Risk</h2>
        <p className="text-sm text-text-muted mt-1">
          Trading safety, read-only state, and risk limits.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassyCard
          title="Read-only Mode"
          neon={readOnly ? "amber" : risk?.kill_switch_enabled ? "red" : "green"}
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-accent-amber font-medium">
                  Read-only mode active
                </p>
                <p className="text-xs text-text-muted mt-0.5">
                  All order actions are blocked
                </p>
              </div>
              <Lock size={32} className="text-accent-amber" />
            </div>
          </div>
          {readOnly ? (
            <div className="w-full py-2.5 rounded-xl text-sm text-center bg-surface-hover/50 text-text-muted border border-surface-border cursor-not-allowed">
              Trading disabled
            </div>
          ) : (
            <button
              onClick={() =>
                killSwitchMutation.mutate(!risk?.kill_switch_enabled)
              }
              className="w-full py-2.5 rounded-xl text-sm font-medium transition-colors bg-surface-hover/50 text-text-muted border border-surface-border cursor-not-allowed"
              disabled
            >
              Trading disabled
            </button>
          )}
        </GlassyCard>

        <GlassyCard title="Connectivity">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-secondary">Moomoo Connection</span>
              <div className="flex items-center gap-2">
                <span
                  className={`status-dot ${
                    risk?.broker_connected
                      ? "status-dot-green"
                      : "status-dot-red"
                  }`}
                />
                <span className="text-sm font-mono">
                  {risk?.broker_connected ? "Connected" : "Disconnected"}
                </span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-secondary">Live Trading</span>
              <span className={`text-sm font-mono ${health?.is_live_trading_enabled ? "text-accent-green" : "text-accent-red"}`}>
                {health?.is_live_trading_enabled ? "Enabled" : "Disabled"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-secondary">Read-only Mode</span>
              <span className={`text-sm font-mono ${readOnly ? "text-accent-amber" : "text-accent-green"}`}>
                {readOnly ? "Active" : "Inactive"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-secondary">Order Actions</span>
              <span className={`text-sm font-mono ${readOnly ? "text-accent-red" : "text-accent-green"}`}>
                {readOnly ? "Blocked" : "Allowed"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-secondary">Trading Blocked</span>
              <span
                className={`text-sm font-mono ${
                  risk?.trading_blocked
                    ? "text-accent-red"
                    : "text-accent-green"
                }`}
              >
                {risk?.trading_blocked ? "Yes" : "No"}
              </span>
            </div>
          </div>
        </GlassyCard>

        <GlassyCard title="Drawdown">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-secondary">Current</span>
              <span
                className={`text-lg font-bold font-mono ${
                  risk?.drawdown_hard_exceeded
                    ? "value-down"
                    : risk?.drawdown_soft_exceeded
                    ? "text-accent-amber"
                    : "text-text-primary"
                }`}
              >
                {formatPercent(risk?.drawdown_pct)}
              </span>
            </div>
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs text-text-muted">
                <span>Soft Limit</span>
                <span>{risk?.max_drawdown_soft_pct}%</span>
              </div>
              <div className="flex items-center justify-between text-xs text-text-muted">
                <span>Hard Limit</span>
                <span>{risk?.max_drawdown_hard_pct}%</span>
              </div>
            </div>
          </div>
        </GlassyCard>
      </div>

      <div className="mt-6">
        <GlassyCard title="Recent Risk Events">
          {risk?.recent_events && risk.recent_events.length > 0 ? (
            <div className="space-y-2">
              {risk.recent_events.map((e) => (
                <div
                  key={e.id}
                  className="flex items-start gap-3 py-2 border-b border-surface-border/30 last:border-0"
                >
                  <span
                    className={`status-dot mt-1 ${
                      e.severity === "ERROR" || e.blocked
                        ? "status-dot-red"
                        : e.severity === "WARNING"
                        ? "status-dot-amber"
                        : "status-dot-green"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-text-primary">{e.message}</p>
                    <p className="text-xs text-text-muted mt-0.5">
                      {e.event_type}
                      {e.symbol ? ` | ${e.symbol}` : ""}
                    </p>
                  </div>
                  <span className="text-xs text-text-muted whitespace-nowrap">
                    {new Date(e.event_time).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-muted text-center py-4">
              No recent risk events
            </p>
          )}
        </GlassyCard>
      </div>
    </div>
  );
}
