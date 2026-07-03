"use client";

import GlassyCard from "@/components/shared/GlassyCard";
import { FlaskConical } from "lucide-react";

export default function BacktestsPage() {
  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-text-primary">Backtests</h2>
        <p className="text-sm text-text-muted mt-1">
          Strategy backtesting engine
        </p>
      </div>

      <GlassyCard>
        <div className="text-center py-16">
          <FlaskConical size={48} className="text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            Coming Soon
          </h3>
          <p className="text-sm text-text-muted max-w-md mx-auto">
            Backtesting engine is under development. Future versions will support
            running the Momentum Relative Strength strategy against historical data
            with configurable parameters and performance reporting.
          </p>
          <div className="mt-6 p-4 rounded-lg bg-surface-hover inline-block text-left">
            <p className="text-xs text-text-muted mb-2">Planned integrations:</p>
            <ul className="text-xs text-text-secondary space-y-1 list-disc list-inside">
              <li>Backtrader for local strategy backtesting</li>
              <li>Historical data from yfinance or moomoo OpenD</li>
              <li>Performance metrics (Sharpe, Sortino, max drawdown)</li>
              <li>Walk-forward optimization</li>
              <li>Monte Carlo simulation</li>
            </ul>
          </div>
        </div>
      </GlassyCard>
    </div>
  );
}
