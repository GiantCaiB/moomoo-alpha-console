import type { BrokerHealthResponse } from "./types";

export function isReadOnlyMode(health: BrokerHealthResponse | null): boolean {
  if (!health) return true;
  return health.read_only === true || health.is_live_trading_enabled === false;
}
