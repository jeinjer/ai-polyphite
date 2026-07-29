import { create } from "zustand";

export type DashboardSection =
  | "home"
  | "markets"
  | "history"
  | "predictions"
  | "agents"
  | "portfolio"
  | "trades"
  | "positions"
  | "performance"
  | "experiments"
  | "sources"
  | "system"
  | "settings";

type UiState = {
  mode: "simple" | "advanced";
  selectedMarketId: string | null;
  setMode: (mode: "simple" | "advanced") => void;
  selectMarket: (marketId: string) => void;
};

export const useUiStore = create<UiState>((set) => ({
  mode: "simple",
  selectedMarketId: null,
  setMode: (mode) => set({ mode }),
  selectMarket: (selectedMarketId) => set({ selectedMarketId }),
}));
