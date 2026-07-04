"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useBrokerHealth } from "@/app/providers";
import GlassyCard from "@/components/shared/GlassyCard";
import { AlertTriangle, CheckCircle, XCircle, Plus, X, RotateCcw, Save, BarChart3 } from "lucide-react";
import type { MarketDataStatusResponse } from "@/lib/types";

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const { data: config, isLoading } = useQuery({
    queryKey: ["config"],
    queryFn: api.config,
  });

  const { health: brokerHealth, isLoading: bhLoading } = useBrokerHealth();

  const { data: mdStatus } = useQuery<MarketDataStatusResponse>({
    queryKey: ["market-data-status"],
    queryFn: api.marketDataStatus,
    refetchInterval: 30_000,
  });

  const {
    data: universeData,
    isLoading: tuLoading,
  } = useQuery({
    queryKey: ["trading-universe"],
    queryFn: api.tradingUniverse,
  });

  const [symbols, setSymbols] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (universeData) {
      setSymbols([...universeData.symbols]);
    }
  }, [universeData]);

  const saveMutation = useMutation({
    mutationFn: (newSymbols: string[]) => api.saveTradingUniverse(newSymbols),
    onSuccess: () => {
      setSaveSuccess(true);
      setSaveError(null);
      queryClient.invalidateQueries({ queryKey: ["trading-universe"] });
      queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
    onError: (err: Error) => {
      setSaveError(err.message);
      setSaveSuccess(false);
      queryClient.invalidateQueries({ queryKey: ["trading-universe"] });
    },
  });

  const resetMutation = useMutation({
    mutationFn: api.deleteTradingUniverse,
    onSuccess: () => {
      setSymbols([]);
      setSaveSuccess(false);
      setSaveError(null);
      queryClient.invalidateQueries({ queryKey: ["trading-universe"] });
      queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
    onError: () => {
      queryClient.invalidateQueries({ queryKey: ["trading-universe"] });
    },
  });

  const handleAdd = () => {
    const trimmed = inputValue.toUpperCase().trim();
    if (!trimmed) return;
    if (symbols.includes(trimmed)) {
      setSaveError(`${trimmed} is already in the universe`);
      return;
    }
    setSymbols((prev) => [...prev, trimmed]);
    setInputValue("");
    setSaveError(null);
    setSaveSuccess(false);
  };

  const handleRemove = (sym: string) => {
    setSymbols((prev) => prev.filter((s) => s !== sym));
    setSaveError(null);
    setSaveSuccess(false);
  };

  const handleReset = () => {
    resetMutation.mutate();
  };

  const handleSave = () => {
    if (symbols.length === 0) {
      setSaveError("Trading universe cannot be empty");
      return;
    }
    setSaveError(null);
    setSaveSuccess(false);
    saveMutation.mutate(symbols);
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-text-primary">Settings</h2>
        <p className="text-sm text-text-muted mt-1">
          Connection, universe, risk, and market data settings.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <GlassyCard title="Connection">
          {isLoading ? (
            <div className="h-20 bg-surface-hover animate-pulse rounded" />
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Broker Mode</span>
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

        <GlassyCard title="Connection Health">
          {bhLoading ? (
            <div className="h-20 bg-surface-hover animate-pulse rounded" />
          ) : brokerHealth ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Moomoo Connection</span>
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
                <span className="text-sm text-text-secondary">Read-only</span>
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
          <div className="space-y-3">
            <p className="text-xs text-text-muted">
              These symbols are scanned by Entry Signals. Position Management uses your actual holdings.
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
                placeholder="Add symbol..."
                className="flex-1 px-3 py-1.5 rounded-lg bg-surface border border-surface-border
                           text-sm font-mono text-text-primary placeholder-text-muted
                           focus:outline-none focus:border-accent-blue"
              />
              <button
                onClick={handleAdd}
                className="flex items-center gap-1 px-3 py-1.5 rounded-xl
                           bg-accent-blue/10 text-accent-blue text-sm font-medium
                           border border-accent-blue/25 hover:bg-accent-blue/15"
              >
                <Plus size={14} />
                Add
              </button>
            </div>

            <div className="flex flex-wrap gap-2 min-h-[2rem]">
              {symbols.map((sym) => (
                <span
                  key={sym}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl
                             bg-surface-hover text-sm font-mono text-text-primary
                             border border-surface-border"
                >
                  {sym}
                  <button
                    onClick={() => handleRemove(sym)}
                    className="text-text-muted hover:text-accent-red transition-colors"
                  >
                    <X size={14} />
                  </button>
                </span>
              ))}
              {symbols.length === 0 && (
                <span className="text-sm text-text-muted">
                  No symbols configured. Add symbols above.
                </span>
              )}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-surface-border">
              <div className="flex items-center gap-2">
                <button
                  onClick={handleReset}
                  disabled={resetMutation.isPending}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl
                             bg-surface-hover text-text-muted text-xs font-medium
                             hover:text-accent-amber transition-colors
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <RotateCcw size={12} />
                  Reset to Default
                </button>
              </div>
              <button
                onClick={handleSave}
                disabled={saveMutation.isPending}
                className="flex items-center gap-1 px-4 py-1.5 rounded-xl
                           bg-accent-green/10 text-accent-green text-sm font-medium
                           border border-accent-green/25 hover:bg-accent-green/15
                           disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Save size={14} />
                {saveMutation.isPending ? "Saving..." : "Save"}
              </button>
            </div>

            {saveError && (
              <div className="flex items-center gap-1.5 text-xs text-accent-red">
                <AlertTriangle size={12} />
                <span>{saveError}</span>
              </div>
            )}
            {saveSuccess && (
              <div className="flex items-center gap-1.5 text-xs text-accent-green">
                <CheckCircle size={12} />
                <span>Trading universe saved. Run Entry Screener to apply changes.</span>
              </div>
            )}
            {universeData?.source === "default" && symbols.length > 0 && (
              <div className="text-xs text-text-muted">
                Source: environment defaults
              </div>
            )}
            {universeData?.source === "database" && (
              <div className="text-xs text-text-muted">
                Source: saved settings
              </div>
            )}
          </div>
        </GlassyCard>

        <GlassyCard title="Order Safety">
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

        <GlassyCard title="Market Data">
          {mdStatus ? (
            <div className="space-y-3">
              <p className="text-xs text-text-muted">
                K-Line Data Provider, cache, and runtime metrics.
              </p>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Provider</span>
                <span className="text-sm font-mono text-accent-green">
                  {mdStatus.provider.toUpperCase()}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Cache Enabled</span>
                <span className={`text-sm font-mono ${mdStatus.cache_enabled ? "text-accent-green" : "text-text-muted"}`}>
                  {mdStatus.cache_enabled ? "YES" : "NO"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Lookback Days</span>
                <span className="text-sm font-mono">{mdStatus.lookback_days}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Extended Lookback</span>
                <span className="text-sm font-mono">{mdStatus.extended_lookback_days}</span>
              </div>
              <div className="border-t border-surface-border pt-3 mt-3">
                <div className="flex items-center gap-2 mb-2">
                  <BarChart3 size={14} className="text-text-muted" />
                  <span className="text-xs font-medium text-text-muted uppercase tracking-wider">Cache Metrics</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-surface-hover rounded p-2">
                    <div className="text-lg font-mono text-accent-blue">{mdStatus.requests}</div>
                    <div className="text-xs text-text-muted">Requests</div>
                  </div>
                  <div className="bg-surface-hover rounded p-2">
                    <div className="text-lg font-mono text-accent-green">{mdStatus.cache_hits}</div>
                    <div className="text-xs text-text-muted">Cache Hits</div>
                  </div>
                  <div className="bg-surface-hover rounded p-2">
                    <div className="text-lg font-mono text-accent-amber">{mdStatus.cache_misses}</div>
                    <div className="text-xs text-text-muted">Cache Misses</div>
                  </div>
                  <div className="bg-surface-hover rounded p-2">
                    <div className="text-lg font-mono text-accent-amber">{mdStatus.upstream_fetches}</div>
                    <div className="text-xs text-text-muted">Upstream Fetches</div>
                  </div>
                  <div className="bg-surface-hover rounded p-2">
                    <div className="text-lg font-mono text-accent-red">{mdStatus.failed}</div>
                    <div className="text-xs text-text-muted">Failed</div>
                  </div>
                  <div className="col-span-2 text-xs text-text-muted">
                    Runtime metrics reset when the backend restarts.
                  </div>
                  {mdStatus.latest_successful_fetch && (
                    <div className="bg-surface-hover rounded p-2 col-span-2">
                      <div className="text-xs font-mono text-text-muted truncate">{mdStatus.latest_successful_fetch}</div>
                      <div className="text-xs text-text-muted">Last Success</div>
                    </div>
                  )}
                </div>
              </div>
              {Object.keys(mdStatus.per_symbol).length > 0 && (
                <div className="border-t border-surface-border pt-3 mt-1">
                  <span className="text-xs font-medium text-text-muted uppercase tracking-wider">Per-Symbol</span>
                  <div className="mt-2 space-y-1 max-h-32 overflow-y-auto">
                    {Object.entries(mdStatus.per_symbol).map(([sym, info]) => (
                      <div key={sym} className="flex items-center justify-between text-xs">
                        <span className="font-mono text-text-primary">{sym}</span>
                        <span className="text-text-muted">{info.bars} bars ({info.source})</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="h-20 bg-surface-hover animate-pulse rounded" />
          )}
        </GlassyCard>
      </div>
    </div>
  );
}
