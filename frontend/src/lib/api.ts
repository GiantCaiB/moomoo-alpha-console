import type {
  HealthResponse,
  ConfigResponse,
  PortfolioSummary,
  PositionResponse,
  OrderResponse,
  SignalResponse,
  RiskStatusResponse,
  WatchlistItemResponse,
  PreviewOrderResponse,
  BrokerHealthResponse,
  TradingUniverseResponse,
  RuntimeStatusResponse,
  RunSignalsResponse,
  MarketDataStatusResponse,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8020";

async function fetcher<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  health: () => fetcher<HealthResponse>("/api/v1/health"),

  config: () => fetcher<ConfigResponse>("/api/v1/config"),

  portfolio: () => fetcher<PortfolioSummary>("/api/v1/portfolio/summary"),

  positions: () => fetcher<PositionResponse[]>("/api/v1/positions"),

  orders: () => fetcher<OrderResponse[]>("/api/v1/orders"),

  previewOrder: (data: {
    symbol: string;
    side: string;
    quantity: number;
    limit_price: number;
    stop_level?: number;
  }) =>
    fetcher<PreviewOrderResponse>("/api/v1/orders/preview", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  approveOrder: (order_id: string) =>
    fetcher<{ success: boolean; order_id?: string; error?: string }>(
      "/api/v1/orders/approve",
      { method: "POST", body: JSON.stringify({ order_id }) }
    ),

  cancelOrder: (order_id: string) =>
    fetcher<{ success: boolean }>("/api/v1/orders/cancel", {
      method: "POST",
      body: JSON.stringify({ order_id }),
    }),

  signals: (includeLocal?: boolean) => {
    const params = includeLocal ? "?include_local=true" : "";
    return fetcher<SignalResponse[]>(`/api/v1/signals${params}`);
  },

  runSignals: () =>
    fetcher<RunSignalsResponse>("/api/v1/signals/run", { method: "POST" }),

  riskStatus: () => fetcher<RiskStatusResponse>("/api/v1/risk/status"),

  toggleKillSwitch: (enabled: boolean) =>
    fetcher<{ success: boolean; kill_switch_enabled: boolean }>(
      "/api/v1/risk/kill-switch",
      { method: "POST", body: JSON.stringify({ enabled }) }
    ),

  watchlist: () => fetcher<WatchlistItemResponse[]>("/api/v1/watchlist"),

  brokerHealth: () => fetcher<BrokerHealthResponse>("/api/v1/broker/health"),

  runtimeStatus: () => fetcher<RuntimeStatusResponse>("/api/v1/runtime/status"),

  deleteStaleSignals: () =>
    fetcher<{ success: boolean; deleted_count: number }>(
      "/api/v1/signals/stale",
      { method: "DELETE" }
    ),

  tradingUniverse: () =>
    fetcher<TradingUniverseResponse>("/api/v1/settings/trading-universe"),

  saveTradingUniverse: (symbols: string[]) =>
    fetcher<TradingUniverseResponse>("/api/v1/settings/trading-universe", {
      method: "PUT",
      body: JSON.stringify({ symbols }),
    }),

  deleteTradingUniverse: () =>
    fetcher<{ success: boolean }>("/api/v1/settings/trading-universe", {
      method: "DELETE",
    }),

  marketDataStatus: () =>
    fetcher<MarketDataStatusResponse>("/api/v1/market-data/status"),
};
