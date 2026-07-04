export function getSourceBadge(dataSource: string | null): {
  label: string;
  className: string;
} {
  switch (dataSource) {
    case "moomoo":
      return {
        label: "MOOMOO",
        className:
          "bg-accent-green/10 text-accent-green border border-accent-green/25",
      };
    case "moomoo_snapshot_plus_yfinance_kline":
      return {
        label: "MOOMOO + YFINANCE",
        className:
          "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/25",
      };
    case "moomoo_positions_plus_yfinance_kline":
      return {
        label: "POSITIONS + K-LINE",
        className:
          "bg-accent-purple/10 text-accent-purple border border-accent-purple/25",
      };
    case "openbb":
      return {
        label: "OPENBB DATA",
        className:
          "bg-accent-blue/10 text-accent-blue border border-accent-blue/25",
      };
    case "vibe_trading":
      return {
        label: "VIBE-TRADING DATA",
        className:
          "bg-accent-purple/10 text-accent-purple border border-accent-purple/25",
      };
    case "local_generated":
      return {
        label: "LOCAL / DEV",
        className:
          "bg-accent-amber/10 text-accent-amber border border-accent-amber/25",
      };
    default:
      return {
        label: "UNKNOWN",
        className: "bg-surface-hover text-text-muted border border-surface-border",
      };
  }
}
