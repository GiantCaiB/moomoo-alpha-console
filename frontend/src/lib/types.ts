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
  price_as_of: string | null;
  bar_source: string | null;
  is_real_market_data: boolean;
  is_tradeable: boolean;
  has_error: boolean;
  failed_filters: string[] | null;
  data_quality_status: string;
  calculated_score_before_filters: number | null;
  run_id: string | null;
  strategy_profile_id: string | null;
  strategy_version: string | null;
}

export interface EntrySignalRunResponse {
  id: string;
  strategy_profile_id: string | null;
  strategy_name: string;
  strategy_version: string | null;
  status: string;
  symbols_scanned: number;
  signals_generated: number;
  data_error_count: number;
  started_at: string;
  finished_at: string | null;
  error_message: string | null;
  parameters_snapshot_json: string | null;
  created_at: string;
}

export interface PositionManagementSignalResponse {
  id: string | null;
  symbol: string;
  signal: string;
  reason: string | null;
  current_price: number | null;
  avg_cost: number | null;
  quantity: number | null;
  gain_pct: number | null;
  suggested_action: string | null;
  suggested_quantity: number | null;
  suggested_trim_pct: number | null;
  tail_mode: boolean;
  weekly_close: number | null;
  weekly_sma20: number | null;
  weekly_sma30: number | null;
  drawdown_from_high: number | null;
  original_cost_basis: number | null;
  highest_price_since_entry: number | null;
  tail_started_at: string | null;
  trim_25_done: boolean | null;
  trim_50_done: boolean | null;
  trim_75_done: boolean | null;
  data_source: string | null;
  price_source: string | null;
  bar_source: string | null;
  is_real_market_data: boolean;
  generated_at: string;
  created_at: string;
  run_id: string | null;
}

export interface PositionSignalRunResponse {
  id: string | null;
  strategy_profile_id: string | null;
  strategy_name: string | null;
  strategy_version: string | null;
  status: string;
  positions_scanned: number;
  signals_generated: number;
  data_error_count: number;
  read_only: boolean;
  error: string | null;
}

export interface DeleteStalePositionSignalsResponse {
  success: boolean;
  deleted_count: number;
  deleted_symbols: string[];
  active_symbols: string[];
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
  run_id: string;
  provider: string;
  market_data_provider: string;
  data_source: string;
  universe_source: string;
  symbols_scanned: string[];
  signals_generated: number;
  data_error_count: number;
  status: string;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  parameters_snapshot_json: string | null;
}

export interface PositionGuidanceRunResponse {
  id: string;
  strategy_profile_id: string | null;
  strategy_name: string;
  strategy_version: string | null;
  status: string;
  positions_scanned: number;
  signals_generated: number;
  data_error_count: number;
  started_at: string;
  finished_at: string | null;
  error_message: string | null;
  parameters_snapshot_json: string | null;
  created_at: string;
}

export interface StaleSignalCountResponse {
  stale_count: number;
  local_or_mock_count: number;
  out_of_universe_count: number;
  stale_symbols: string[];
  local_or_mock_symbols: string[];
  out_of_universe_symbols: string[];
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

export interface PriceFreshnessInfo {
  current_price: number | null;
  price_source: string;
  price_timestamp: string | null;
  error: string | null;
}

export interface CurrentPricesResponse {
  prices: Record<string, PriceFreshnessInfo>;
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

export interface StrategyProfileResponse {
  id: string;
  name: string;
  strategy_type: string;
  strategy_key: string;
  version: string;
  description: string | null;
  parameters: Record<string, unknown> | null;
  rules_summary: Record<string, unknown> | null;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
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
