import axios from "axios";

const API_URL = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

export const marketsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get("/markets", { params }),
  discover: () => api.post("/markets/discover"),
};

export const tradesApi = {
  list: (params?: Record<string, unknown>) =>
    api.get("/trades", { params }),
  stats: () => api.get("/trades/stats/summary"),
};

export const aiApi = {
  status: () => api.get("/ai/status"),
  logs: (limit = 10) => api.get(`/ai/logs?limit=${limit}`),
};

export const systemApi = {
  health: () => api.get("/system/health"),
  risk: () => api.get("/system/risk"),
};
