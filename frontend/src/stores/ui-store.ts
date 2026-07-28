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
  section: DashboardSection;
  selectedMarketId: string | null;
  setMode: (mode: "simple" | "advanced") => void;
  setSection: (section: DashboardSection) => void;
  selectMarket: (marketId: string) => void;
};

export const useUiStore = create<UiState>((set) => ({
  mode: "simple",
  section: "home",
  selectedMarketId: null,
  setMode: (mode) => set({ mode }),
  setSection: (section) => set({ section }),
  selectMarket: (selectedMarketId) => set({ selectedMarketId }),
}));
