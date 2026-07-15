export function formatMoney(
  value: number | null | undefined,
  currency?: string
): string {
  if (value === null || value === undefined) return "--";
  const prefix = value < 0 ? "-$" : "$";
  const abs = Math.abs(value);
  const formatted = abs.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const suffix = currency && currency !== "USD" ? ` ${currency}` : "";
  return `${prefix}${formatted}${suffix}`;
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "--";
  const prefix = value < 0 ? "-" : "";
  const formatted = Math.abs(value).toFixed(2);
  return `${prefix}${formatted}%`;
}

export function formatQuantity(value: number | null | undefined): string {
  if (value === null || value === undefined) return "--";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 6,
  });
}

export function formatPrice(
  value: number | null | undefined,
  currency?: string
): string {
  if (value === null || value === undefined) return "--";
  const prefix = value < 0 ? "-$" : "$";
  const abs = Math.abs(value);
  const formatted = abs.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const suffix = currency && currency !== "USD" ? ` ${currency}` : "";
  return `${prefix}${formatted}${suffix}`;
}
