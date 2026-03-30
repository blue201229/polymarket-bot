import { create } from "zustand";
import type { RiskParams, SystemHealth } from "@/lib/api";

interface SystemState {
  health: SystemHealth | null;
  riskParams: RiskParams | null;
  aiEnabled: boolean;
  isLoading: boolean;
  lastUpdate: Date | null;
  setHealth: (health: SystemHealth) => void;
  setRiskParams: (params: RiskParams) => void;
  setLoading: (loading: boolean) => void;
}

export const useSystemStore = create<SystemState>((set) => ({
  health: null,
  riskParams: null,
  aiEnabled: true,
  isLoading: false,
  lastUpdate: null,
  setHealth: (health) => set({ health, aiEnabled: health.ai_available, lastUpdate: new Date() }),
  setRiskParams: (riskParams) => set({ riskParams }),
  setLoading: (isLoading) => set({ isLoading }),
}));
