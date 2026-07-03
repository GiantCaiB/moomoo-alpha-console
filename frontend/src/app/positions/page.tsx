"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatPercent } from "@/lib/format";
import GlassyCard from "@/components/shared/GlassyCard";
import PriceDisplay from "@/components/shared/PriceDisplay";

export default function PositionsPage() {
  const { data: positions, isLoading } = useQuery({
    queryKey: ["positions"],
    queryFn: api.positions,
  });

  const { data: portfolio } = useQuery({
    queryKey: ["portfolio"],
    queryFn: api.portfolio,
  });

  const activePositions = positions?.filter((p) => (p.quantity ?? 0) > 0) ?? [];

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-text-primary">Positions</h2>
        <p className="text-sm text-text-muted mt-1">
          Current open positions ({activePositions.length})
        </p>
      </div>

      {isLoading ? (
        <div className="h-40 bg-surface-hover animate-pulse rounded-xl" />
      ) : activePositions.length > 0 ? (
        <GlassyCard>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-text-muted text-xs uppercase tracking-wider border-b border-surface-border">
                  <th className="text-left py-3 pr-4">Symbol</th>
                  <th className="text-right py-3 pr-4">Quantity</th>
                  <th className="text-right py-3 pr-4">Avg Cost</th>
                  <th className="text-right py-3 pr-4">Current Price</th>
                  <th className="text-right py-3 pr-4">Unrealized P&L</th>
                  <th className="text-right py-3 pr-4">Day P&L</th>
                  <th className="text-right py-3 pr-4">Stop Level</th>
                  <th className="text-right py-3 pr-4">% Portfolio</th>
                </tr>
              </thead>
              <tbody>
                {activePositions.map((pos) => (
                  <tr
                    key={pos.id}
                    className="border-b border-surface-border/30 hover:bg-surface-hover/30 transition-colors"
                  >
                    <td className="py-3 pr-4 font-mono font-bold text-text-primary">
                      {pos.symbol}
                    </td>
                    <td className="py-3 pr-4 text-right font-mono">
                      {pos.quantity}
                    </td>
                    <td className="py-3 pr-4 text-right font-mono">
                      <PriceDisplay value={pos.avg_cost} prefix="$" />
                    </td>
                    <td className="py-3 pr-4 text-right font-mono">
                      <PriceDisplay value={pos.current_price} prefix="$" />
                    </td>
                    <td
                      className={`py-3 pr-4 text-right font-mono ${
                        (pos.unrealized_pnl ?? 0) >= 0
                          ? "value-up"
                          : "value-down"
                      }`}
                    >
                      <PriceDisplay value={pos.unrealized_pnl} prefix="$" colorize />
                    </td>
                    <td
                      className={`py-3 pr-4 text-right font-mono ${
                        (pos.day_pnl ?? 0) >= 0 ? "value-up" : "value-down"
                      }`}
                    >
                      <PriceDisplay value={pos.day_pnl} prefix="$" colorize />
                    </td>
                    <td className="py-3 pr-4 text-right font-mono text-accent-red">
                      <PriceDisplay value={pos.stop_level} prefix="$" />
                    </td>
                    <td className="py-3 text-right font-mono text-text-secondary">
                      {formatPercent(pos.position_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassyCard>
      ) : (
        <GlassyCard>
          <div className="text-center py-12">
            <p className="text-text-muted text-sm">No open positions</p>
          </div>
        </GlassyCard>
      )}
    </div>
  );
}
