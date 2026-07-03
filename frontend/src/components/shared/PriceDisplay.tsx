import { clsx } from "clsx";

interface PriceDisplayProps {
  value: number | null | undefined;
  prefix?: string;
  suffix?: string;
  colorize?: boolean;
  decimals?: number;
  className?: string;
}

export default function PriceDisplay({
  value,
  prefix = "",
  suffix = "",
  colorize = false,
  decimals = 2,
  className,
}: PriceDisplayProps) {
  if (value === null || value === undefined) {
    return <span className="text-text-muted">--</span>;
  }

  const formatted = value.toFixed(decimals);
  const isPositive = value > 0;
  const isNegative = value < 0;

  return (
    <span
      className={clsx(
        "font-mono tabular-nums",
        colorize && isPositive && "value-up",
        colorize && isNegative && "value-down",
        className
      )}
    >
      {prefix}
      {isNegative && "-"}${Math.abs(Number(formatted)).toFixed(decimals)}
      {suffix}
    </span>
  );
}
