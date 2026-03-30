import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

export interface Market {
  id: string;
  condition_id: string;
  question: string;
  category: string;
  status: string;
  volume: number;
  volume_24h: number;
  liquidity: number;
  spread: number | null;
  ai_score: number | null;
  ai_reasoning: string | null;
  ai_tags: string[];
  outcomes: { token_id: string; outcome: string; price: number }[];
  source_url: string;
}

export interface Trade {
  id: string;
  condition_id: string;
  outcome: string;
  side: string;
  status: string;
  price: number;
  size: number;
  filled_size: number;
  filled_price: number | null;
  strategy: string;
  is_paper: boolean;
  ai_confidence: number | null;
  ai_size_modifier: number | null;
  ai_approved: boolean | null;
  ai_skip_reason: string | null;
  pnl: number | null;
  created_at: string;
}

export interface Position {
  id: string;
  condition_id: string;
  outcome: string;
  side: string;
  size: number;
  avg_entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  realized_pnl: number;
  strategy: string;
  is_paper: boolean;
  is_open: boolean;
  created_at: string;
}

export const fetchMarkets = (params?: Record<string, any>) =>
  api.get('/markets', { params }).then((r) => r.data);

export const fetchTrades = (params?: Record<string, any>) =>
  api.get('/trades', { params }).then((r) => r.data);

export const fetchPositions = (params?: Record<string, any>) =>
  api.get('/positions', { params }).then((r) => r.data);

export const fetchWallets = () =>
  api.get('/wallets').then((r) => r.data);

export const fetchPerformance = (days: number = 7) =>
  api.get('/performance/summary', { params: { days } }).then((r) => r.data);

export const fetchAILogs = (params?: Record<string, any>) =>
  api.get('/ai/logs', { params }).then((r) => r.data);

export const fetchAIImpact = (days: number = 30) =>
  api.get('/ai/impact', { params: { days } }).then((r) => r.data);

export const runOptimization = (days: number = 7) =>
  api.post('/ai/optimize', null, { params: { days } }).then((r) => r.data);

export const runPostTradeAnalysis = (days: number = 7) =>
  api.post('/ai/analyze', null, { params: { days } }).then((r) => r.data);

export const fetchAlerts = (params?: Record<string, any>) =>
  api.get('/alerts', { params }).then((r) => r.data);

export const acknowledgeAlert = (alertId: string) =>
  api.post(`/alerts/${alertId}/acknowledge`).then((r) => r.data);

export const fetchTradeStats = () =>
  api.get('/trades/stats').then((r) => r.data);

export const fetchSystemHealth = () =>
  api.get('/system/health').then((r) => r.data);

export default api;
