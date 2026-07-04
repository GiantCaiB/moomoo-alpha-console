"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { isReadOnlyMode } from "@/lib/readonly";
import { useBrokerHealth } from "@/app/providers";
import { formatPrice } from "@/lib/format";
import GlassyCard from "@/components/shared/GlassyCard";
import { Eye, ShieldBan } from "lucide-react";

export default function WatchlistPage() {
  const { health } = useBrokerHealth();
  const readOnly = isReadOnlyMode(health);

  const { data: universe, isLoading: tuLoading } = useQuery({
    queryKey: ["trading-universe"],
    queryFn: api.tradingUniverse,
  });

  const { data: watchlist, isLoading: wlLoading } = useQuery({
    queryKey: ["watchlist"],
    queryFn: api.watchlist,
  });

  const symbols: string[] = universe?.symbols ?? [];

  const isLoading = tuLoading || wlLoading;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-text-primary">Watchlist</h2>
          <p className="text-sm text-text-muted mt-1">
            Trading universe &mdash; {symbols.length} symbols monitored
          </p>
        </div>
        {readOnly && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-amber/10 border border-accent-amber/30 text-accent-amber text-xs font-medium">
            <ShieldBan size={14} />
            READ-ONLY
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="h-20 bg-surface-hover animate-pulse rounded-xl"
            />
          ))}
        </div>
      ) : symbols.length === 0 ? (
        <GlassyCard>
          <div className="text-center py-12">
            <Eye size={32} className="mx-auto mb-3 text-text-muted/40" />
            <p className="text-text-muted text-sm">
              No symbols configured. Add symbols to your trading universe in Settings.
            </p>
          </div>
        </GlassyCard>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {symbols.map((sym) => {
            const wlItem = watchlist?.find(
              (w) => w.symbol === sym
            );
            const addedPrice = wlItem?.added_price ?? null;
            return (
              <GlassyCard key={sym}>
                <div className="flex flex-col">
                  <span className="font-mono font-bold text-text-primary text-sm">
                    {sym}
                  </span>
                  <span className="text-xs text-text-muted mt-1">
                    Added:{" "}
                    {addedPrice !== null
                      ? formatPrice(addedPrice)
                      : "--"}
                  </span>
                </div>
              </GlassyCard>
            );
          })}
        </div>
      )}
    </div>
  );
}
