"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import GlassyCard from "@/components/shared/GlassyCard";

export default function SettingsPage() {
  const { data: config, isLoading } = useQuery({
    queryKey: ["config"],
    queryFn: api.config,
  });

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-text-primary">Settings</h2>
        <p className="text-sm text-text-muted mt-1">
          Application configuration
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <GlassyCard title="Broker Configuration">
          {isLoading ? (
            <div className="h-20 bg-surface-hover animate-pulse rounded" />
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Mode</span>
                <span className="text-sm font-mono text-accent-green">
                  {config?.broker_mode?.toUpperCase() || "MOCK"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Trading Enabled</span>
                <span
                  className={`text-sm font-mono ${
                    config?.trading_enabled
                      ? "text-accent-red"
                      : "text-text-muted"
                  }`}
                >
                  {config?.trading_enabled ? "YES" : "NO"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">OpenD Host</span>
                <span className="text-sm font-mono text-text-primary">
                  {config?.opend_host}:{config?.opend_port}
                </span>
              </div>
            </div>
          )}
        </GlassyCard>

        <GlassyCard title="Risk Limits">
          {isLoading ? (
            <div className="h-20 bg-surface-hover animate-pulse rounded" />
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">
                  Max Position Size
                </span>
                <span className="text-sm font-mono">
                  {config?.max_position_pct}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">
                  Max Risk Per Trade
                </span>
                <span className="text-sm font-mono">
                  {config?.max_risk_per_trade_pct}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">
                  Daily Loss Limit
                </span>
                <span className="text-sm font-mono">
                  {config?.daily_loss_limit_pct}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">
                  Max Drawdown (Soft/Hard)
                </span>
                <span className="text-sm font-mono">
                  {config?.max_drawdown_soft_pct}% /{" "}
                  {config?.max_drawdown_hard_pct}%
                </span>
              </div>
            </div>
          )}
        </GlassyCard>

        <GlassyCard title="Trading Universe">
          {isLoading ? (
            <div className="h-20 bg-surface-hover animate-pulse rounded" />
          ) : (
            <div className="flex flex-wrap gap-2">
              {config?.universe_symbols?.map((sym) => (
                <span
                  key={sym}
                  className="px-3 py-1.5 rounded-lg bg-surface-hover text-sm font-mono
                             text-text-primary border border-surface-border"
                >
                  {sym}
                </span>
              ))}
            </div>
          )}
        </GlassyCard>

        <GlassyCard title="Allowed Order Types">
          {isLoading ? (
            <div className="h-20 bg-surface-hover animate-pulse rounded" />
          ) : (
            <div className="flex flex-wrap gap-2">
              {config?.allowed_order_types?.map((type) => (
                <span
                  key={type}
                  className="px-3 py-1.5 rounded-lg bg-accent-blue/10 text-sm font-mono
                             text-accent-blue border border-accent-blue/30"
                >
                  {type}
                </span>
              ))}
            </div>
          )}
        </GlassyCard>
      </div>
    </div>
  );
}
