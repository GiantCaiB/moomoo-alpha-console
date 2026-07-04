export function getSourceBadge(dataSource: string | null): {
  label: string;
  className: string;
} {
  switch (dataSource) {
    case "moomoo":
      return {
        label: "MOOMOO DATA",
        className:
          "bg-accent-green/20 text-accent-green border border-accent-green/30",
      };
    case "moomoo_snapshot_plus_yfinance_kline":
      return {
        label: "MOOMOO + YFINANCE",
        className:
          "bg-accent-green/20 text-accent-green border border-accent-green/30",
      };
    case "openbb":
      return {
        label: "OPENBB DATA",
        className:
          "bg-accent-blue/20 text-accent-blue border border-accent-blue/30",
      };
    case "vibe_trading":
      return {
        label: "VIBE-TRADING DATA",
        className:
          "bg-accent-purple/20 text-accent-purple border border-accent-purple/30",
      };
    case "local_generated":
      return {
        label: "LOCAL GENERATED DATA",
        className:
          "bg-accent-amber/20 text-accent-amber border border-accent-amber/30",
      };
    default:
      return {
        label: "MOCK DATA",
        className: "bg-surface-hover text-text-muted border border-surface-border",
      };
  }
}
