export interface HealthResponse {
  status: string;
  version: string;
  broker_mode: string;
  broker_connected: boolean;
  database_ok: boolean;
  uptime_seconds: number;
}

export interface ConfigResponse {
  broker_mode: string;
  trading_enabled: boolean;
  opend_host: string;
  opend_port: number;
  max_position_pct: number;
  max_risk_per_trade_pct: number;
  daily_loss_limit_pct: number;
  max_drawdown_soft_pct: number;
  max_drawdown_hard_pct: number;
  universe_symbols: string[];
  allowed_order_types: string[];
}

export interface PortfolioSummary {
  total_value: number;
  cash: number;
  positions_value: number;
  day_pnl: number;
  day_pnl_pct: number;
  total_pnl: number;
  total_pnl_pct: number;
  drawdown_pct: number;
  num_positions: number;
  num_open_orders: number;
  currency: string;
}

export interface PositionResponse {
  id: string;
  symbol: string;
  quantity: number;
  avg_cost: number;
  current_price: number | null;
  unrealized_pnl: number | null;
  day_pnl: number | null;
  stop_level: number | null;
  position_pct: number | null;
  status: string;
}

export interface OrderResponse {
  id: string;
  symbol: string;
  side: string;
  order_type: string;
  quantity: number;
  filled_quantity: number;
  limit_price: number | null;
  stop_price: number | null;
  status: string;
  reason: string | null;
  risk_check_passed: boolean | null;
  risk_details: string | null;
  signal_id: string | null;
  created_at: string;
  submitted_at: string | null;
  filled_at: string | null;
  cancelled_at: string | null;
  notes: string | null;
}

export interface SignalScoreResponse {
  category: string;
  score: number;
  max_score: number;
  details: string | null;
}

export interface SignalResponse {
  id: string;
  symbol: string;
  verdict: string;
  total_score: number;
  scores: SignalScoreResponse[];
  reason: string | null;
  entry_min: number | null;
  entry_max: number | null;
  stop_level: number | null;
  target_size_pct: number | null;
  risk_amount: number | null;
  invalidation: string | null;
  current_price: number | null;
  approved: boolean | null;
  signal_date: string;
  created_at: string;
  strategy_name: string | null;
  data_source: string | null;
  generated_at: string | null;
  universe: string[] | null;
  price_source: string | null;
  bar_source: string | null;
  is_real_market_data: boolean;
  is_tradeable: boolean;
  has_error: boolean;
  failed_filters: string[] | null;
  data_quality_status: string;
  calculated_score_before_filters: number | null;
}

export interface RiskStatusResponse {
  kill_switch_enabled: boolean;
  broker_connected: boolean;
  daily_loss_pct: number;
  drawdown_pct: number;
  daily_loss_limit_pct: number;
  max_drawdown_soft_pct: number;
  max_drawdown_hard_pct: number;
  daily_loss_exceeded: boolean;
  drawdown_soft_exceeded: boolean;
  drawdown_hard_exceeded: boolean;
  recent_events: RiskEvent[];
  trading_blocked: boolean;
}

export interface RiskEvent {
  id: string;
  event_type: string;
  severity: string;
  symbol: string | null;
  message: string;
  blocked: boolean;
  event_time: string;
}

export interface TradingUniverseResponse {
  symbols: string[];
  source: string;
}

export interface RuntimeStatusResponse {
  broker_mode: string;
  broker_adapter: string;
  market_data_provider: string;
  research_provider: string;
  mock_enabled: boolean;
  data_source: string;
  account_environment: string;
  read_only: boolean;
  is_live_trading_enabled: boolean;
  trading_universe_count: number;
  universe_source: string;
}

export interface RunSignalsResponse {
  success: boolean;
  strategy_run_id: string;
  provider: string;
  market_data_provider: string;
  data_source: string;
  universe_source: string;
  symbols_scanned: string[];
  signals_generated: number;
  data_error_count: number;
  status: string;
  error: string | null;
}

export interface WatchlistItemResponse {
  id: string;
  symbol: string;
  list_name: string;
  sort_order: number;
  notes: string | null;
  added_price: number | null;
}

export interface PreviewOrderResponse {
  allowed: boolean;
  reasons: string[];
  warnings: string[];
  max_allowed_quantity: number | null;
}

export interface Quote {
  symbol: string;
  bid: number | null;
  ask: number | null;
  last: number | null;
  change: number | null;
  change_pct: number | null;
}

export interface MarketDataStatusResponse {
  provider: string;
  cache_enabled: boolean;
  lookback_days: number;
  extended_lookback_days: number;
  requests: number;
  cache_hits: number;
  cache_misses: number;
  upstream_fetches: number;
  failed: number;
  latest_successful_fetch: string | null;
  per_symbol: Record<string, { bars: number; source: string; last_checked: string }>;
}

export interface BrokerHealthResponse {
  broker_mode: string;
  connected: boolean;
  data_source: string;
  account_environment: string;
  is_real_account_data: boolean;
  is_live_trading_enabled: boolean;
  read_only: boolean;
  opend_host: string;
  opend_port: number;
  trd_env: string;
  warnings: string[];
  error: string | null;
}
