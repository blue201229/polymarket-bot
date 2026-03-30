import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

// Types
export interface Market {
  id: string;
  condition_id: string;
  question: string;
  category?: string;
  best_bid?: number;
  best_ask?: number;
  mid_price?: number;
  spread_pct?: number;
  volume_24h: number;
  liquidity: number;
  active: boolean;
  closed: boolean;
  end_date?: string;
  ai_score?: number;
  ai_reasoning?: string;
  ai_tags?: string;
  ai_scored_at?: string;
  created_at: string;
  updated_at: string;
}

export interface Trade {
  id: string;
  condition_id: string;
  side: string;
  outcome: string;
  source: string;
  status: string;
  size_usdc: number;
  target_price: number;
  executed_price?: number;
  slippage_pct?: number;
  is_paper: boolean;
  pnl_usdc?: number;
  pnl_pct?: number;
  risk_approved: boolean;
  risk_rejection_reason?: string;
  ai_confidence?: number;
  ai_decision?: string;
  ai_reasoning?: string;
  ai_overridden: boolean;
  created_at: string;
  executed_at?: string;
}

export interface Wallet {
  id: string;
  address: string;
  label?: string;
  is_tracked: boolean;
  copy_trade_enabled: boolean;
  total_trades: number;
  win_rate?: number;
  avg_pnl_pct?: number;
  total_volume_usdc: number;
  ai_quality_score?: number;
  ai_strategy_class?: string;
  ai_confidence?: number;
  ai_analysis_summary?: string;
  last_trade_at?: string;
  created_at: string;
}

export interface AILog {
  id: string;
  component: string;
  model: string;
  latency_ms: number;
  cache_hit: boolean;
  success: boolean;
  output_parsed?: Record<string, unknown>;
  created_at: string;
}

export interface RiskParams {
  max_position_size_usdc: number;
  max_total_exposure_usdc: number;
  max_positions: number;
  min_liquidity: number;
  max_spread_pct: number;
  max_slippage_pct: number;
  paper_trading: boolean;
  trading_paused: boolean;
  pause_reason?: string;
}

export interface SystemHealth {
  status: string;
  version: string;
  paper_trading: boolean;
  ai_enabled: boolean;
  ai_available: boolean;
}

// API calls
export const marketsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<{ markets: Market[]; total: number; page: number; limit: number }>("/markets", { params }),
  get: (conditionId: string) => api.get<Market>(`/markets/${conditionId}`),
  discover: (params?: Record<string, unknown>) => api.post("/markets/discover", null, { params }),
  score: (conditionId: string) => api.post("/markets/score", { condition_id: conditionId }),
};

export const tradesApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<{ trades: Trade[]; total: number }>("/trades", { params }),
  get: (id: string) => api.get<Trade>(`/trades/${id}`),
  stats: (params?: Record<string, unknown>) => api.get("/trades/stats/summary", { params }),
  place: (data: Record<string, unknown>) => api.post<Trade>("/trades", data),
};

export const walletsApi = {
  list: (params?: Record<string, unknown>) => api.get<Wallet[]>("/wallets", { params }),
  add: (data: Record<string, unknown>) => api.post<Wallet>("/wallets", data),
  remove: (id: string) => api.delete(`/wallets/${id}`),
  trades: (id: string) => api.get(`/wallets/${id}/trades`),
};

export const aiApi = {
  status: () => api.get("/ai/status"),
  logs: (params?: Record<string, unknown>) => api.get<AILog[]>("/ai/logs", { params }),
  filterSignal: (data: Record<string, unknown>) => api.post("/ai/filter-signal", data),
  optimize: () => api.get("/ai/optimize"),
  anomalies: (conditionId: string) => api.get(`/ai/anomalies/${conditionId}`),
};

export const systemApi = {
  health: () => api.get<SystemHealth>("/system/health"),
  risk: () => api.get<RiskParams>("/system/risk"),
  updateRisk: (data: Partial<RiskParams>) => api.put<RiskParams>("/system/risk", data),
  pause: (reason?: string) => api.post(`/system/trading/pause?reason=${reason || "operator_request"}`),
  resume: () => api.post("/system/trading/resume"),
};
