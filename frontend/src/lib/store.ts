import { create } from "zustand";
import type {
  PortfolioSummary,
  PositionResponse,
  OrderResponse,
  SignalResponse,
  RiskStatusResponse,
} from "./types";

interface AppState {
  portfolio: PortfolioSummary | null;
  positions: PositionResponse[];
  orders: OrderResponse[];
  signals: SignalResponse[];
  risk: RiskStatusResponse | null;
  killSwitch: boolean;

  setPortfolio: (p: PortfolioSummary) => void;
  setPositions: (p: PositionResponse[]) => void;
  setOrders: (o: OrderResponse[]) => void;
  setSignals: (s: SignalResponse[]) => void;
  setRisk: (r: RiskStatusResponse) => void;
  setKillSwitch: (k: boolean) => void;
}

export const useStore = create<AppState>((set) => ({
  portfolio: null,
  positions: [],
  orders: [],
  signals: [],
  risk: null,
  killSwitch: false,

  setPortfolio: (portfolio) => set({ portfolio }),
  setPositions: (positions) => set({ positions }),
  setOrders: (orders) => set({ orders }),
  setSignals: (signals) => set({ signals }),
  setRisk: (risk) => set({ risk }),
  setKillSwitch: (killSwitch) => set({ killSwitch }),
}));
