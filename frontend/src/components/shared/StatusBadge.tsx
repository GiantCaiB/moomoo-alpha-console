import { clsx } from "clsx";

interface StatusBadgeProps {
  status: string;
  className?: string;
}

const variants: Record<string, string> = {
  BUY_STARTER: "bg-accent-green/10 text-accent-green border border-accent-green/25",
  WATCH: "bg-accent-amber/10 text-accent-amber border border-accent-amber/25",
  AVOID: "bg-accent-red/8 text-accent-red border border-accent-red/30",
  OPEN: "bg-accent-blue/10 text-accent-blue border border-accent-blue/25",
  CLOSED: "bg-text-muted/10 text-text-secondary border border-surface-border",
  PENDING: "bg-accent-amber/10 text-accent-amber border border-accent-amber/25",
  SUBMITTED: "bg-accent-blue/10 text-accent-blue border border-accent-blue/25",
  FILLED: "bg-accent-green/10 text-accent-green border border-accent-green/25",
  CANCELLED: "bg-text-muted/10 text-text-secondary border border-surface-border",
  REJECTED: "bg-accent-red/10 text-accent-red border border-accent-red/25",
  FAILED: "bg-accent-red/10 text-accent-red border border-accent-red/25",
  HOLD: "bg-text-muted/10 text-text-secondary border border-surface-border",
  TRIM_PROFIT: "bg-accent-amber/10 text-accent-amber border border-accent-amber/25",
  ENTER_TAIL_MODE: "bg-accent-purple/10 text-accent-purple border border-accent-purple/25",
  HOLD_TAIL: "bg-accent-green/10 text-accent-green border border-accent-green/25",
  TRIM_TAIL: "bg-accent-amber/10 text-accent-amber border border-accent-amber/25",
  EXIT_TAIL: "bg-accent-red/10 text-accent-red border border-accent-red/25",
  REVIEW_POSITION: "bg-accent-amber/10 text-accent-amber border border-accent-amber/25",
  STOP_ADDING: "bg-accent-amber/10 text-accent-amber border border-accent-amber/25",
  REDUCE_RISK: "bg-accent-red/10 text-accent-red border border-accent-red/25",
  EXIT_POSITION: "bg-accent-red/10 text-accent-red border border-accent-red/25",
  DATA_ERROR: "bg-accent-red/10 text-accent-red border border-accent-red/25",
};

const labels: Record<string, string> = {
  BUY_STARTER: "Buy Starter",
  WATCH: "Watch",
  AVOID: "Avoid",
  OPEN: "Open",
  CLOSED: "Closed",
  PENDING: "Pending",
  SUBMITTED: "Submitted",
  FILLED: "Filled",
  CANCELLED: "Cancelled",
  REJECTED: "Rejected",
  FAILED: "Failed",
  HOLD: "Hold",
  TRIM_PROFIT: "Trim Profit",
  ENTER_TAIL_MODE: "Enter Tail Mode",
  HOLD_TAIL: "Hold Tail",
  TRIM_TAIL: "Trim Tail",
  EXIT_TAIL: "Exit Tail",
  REVIEW_POSITION: "Review",
  STOP_ADDING: "Stop Adding",
  REDUCE_RISK: "Reduce Risk",
  EXIT_POSITION: "Exit Review",
  DATA_ERROR: "Data Issue",
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium tracking-tight",
        variants[status] || "bg-surface-hover text-text-secondary",
        className
      )}
    >
      {labels[status] || status}
    </span>
  );
}
