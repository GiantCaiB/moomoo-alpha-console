"use client";

import GlassyCard from "@/components/shared/GlassyCard";
import { FlaskConical } from "lucide-react";

export default function BacktestsPage() {
  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-text-primary">Labs</h2>
        <p className="text-sm text-text-muted mt-1">
          Backtesting and experiments coming soon.
        </p>
      </div>

      <GlassyCard>
        <div className="text-center py-16">
          <FlaskConical size={48} className="text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-text-primary mb-2">Coming Soon</h3>
          <p className="text-sm text-text-muted max-w-md mx-auto">
            Future versions will support backtesting, strategy comparison, and
            market replay.
          </p>
          <div className="mt-6 p-4 rounded-xl bg-surface-hover/40 inline-block text-left border border-surface-border">
            <p className="text-xs text-text-muted mb-2">Planned modules:</p>
            <ul className="text-xs text-text-secondary space-y-1 list-disc list-inside">
              <li>Backtesting</li>
              <li>Strategy comparison</li>
              <li>Walk-forward optimization</li>
              <li>Market replay</li>
            </ul>
          </div>
        </div>
      </GlassyCard>
    </div>
  );
}
