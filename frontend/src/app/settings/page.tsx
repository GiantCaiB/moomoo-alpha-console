"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useBrokerHealth } from "@/app/providers";
import GlassyCard from "@/components/shared/GlassyCard";
import { AlertTriangle, CheckCircle, XCircle } from "lucide-react";

export default function SettingsPage() {
  const { data: config, isLoading } = useQuery({
    queryKey: ["config"],
    queryFn: api.config,
  });

  const { health: brokerHealth, isLoading: bhLoading } = useBrokerHealth();

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

        <GlassyCard title="Broker Health">
          {bhLoading ? (
            <div className="h-20 bg-surface-hover animate-pulse rounded" />
          ) : brokerHealth ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Status</span>
                <div className="flex items-center gap-2">
                  {brokerHealth.connected ? (
                    <CheckCircle size={16} className="text-accent-green" />
                  ) : (
                    <XCircle size={16} className="text-accent-red" />
                  )}
                  <span
                    className={`text-sm font-mono ${
                      brokerHealth.connected
                        ? "text-accent-green"
                        : "text-accent-red"
                    }`}
                  >
                    {brokerHealth.connected ? "Connected" : "Disconnected"}
                  </span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Data Source</span>
                <span className="text-sm font-mono text-text-primary">
                  {brokerHealth.data_source}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Account Environment</span>
                <span className="text-sm font-mono text-text-primary">
                  {brokerHealth.account_environment}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Real Account Data</span>
                <span
                  className={`text-sm font-mono ${
                    brokerHealth.is_real_account_data
                      ? "text-accent-green"
                      : "text-text-muted"
                  }`}
                >
                  {brokerHealth.is_real_account_data ? "YES" : "NO"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Live Trading</span>
                <span
                  className={`text-sm font-mono ${
                    brokerHealth.is_live_trading_enabled
                      ? "text-accent-red"
                      : "text-text-muted"
                  }`}
                >
                  {brokerHealth.is_live_trading_enabled ? "ENABLED" : "DISABLED"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Read-Only</span>
                <span className="text-sm font-mono text-accent-amber">
                  {brokerHealth.read_only ? "YES" : "NO"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">OpenD Host</span>
                <span className="text-sm font-mono text-text-primary">
                  {brokerHealth.opend_host}:{brokerHealth.opend_port}
                </span>
              </div>
              {brokerHealth.trd_env && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-secondary">Trade Env</span>
                  <span className="text-sm font-mono text-text-primary">
                    {brokerHealth.trd_env}
                  </span>
                </div>
              )}
              {brokerHealth.warnings.length > 0 && (
                <div className="mt-2 space-y-1">
                  {brokerHealth.warnings.map((w, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-1.5 text-xs text-accent-amber"
                    >
                      <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                      <span>{w}</span>
                    </div>
                  ))}
                </div>
              )}
              {brokerHealth.error && (
                <div className="flex items-start gap-1.5 text-xs text-accent-red">
                  <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                  <span>{brokerHealth.error}</span>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-text-muted">No health data</p>
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
