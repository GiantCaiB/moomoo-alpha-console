import { clsx } from "clsx";

interface StatusBadgeProps {
  status: string;
  className?: string;
}

const variants: Record<string, string> = {
  BUY_STARTER: "bg-accent-green/10 text-accent-green border border-accent-green/30",
  WATCH: "bg-accent-amber/10 text-accent-amber border border-accent-amber/30",
  AVOID: "bg-accent-red/10 text-accent-red border border-accent-red/30",
  OPEN: "bg-accent-blue/10 text-accent-blue border border-accent-blue/30",
  CLOSED: "bg-text-muted/10 text-text-muted border border-text-muted/30",
  PENDING: "bg-accent-amber/10 text-accent-amber border border-accent-amber/30",
  SUBMITTED: "bg-accent-blue/10 text-accent-blue border border-accent-blue/30",
  FILLED: "bg-accent-green/10 text-accent-green border border-accent-green/30",
  CANCELLED: "bg-text-muted/10 text-text-muted border border-text-muted/30",
  REJECTED: "bg-accent-red/10 text-accent-red border border-accent-red/30",
  FAILED: "bg-accent-red/10 text-accent-red border border-accent-red/30",
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium",
        variants[status] || "bg-surface-hover text-text-secondary",
        className
      )}
    >
      {status}
    </span>
  );
}
