import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
});

export const fetchMarkets = (limit: number = 20) =>
  api.get('/markets', { params: { limit } }).then(r => r.data);

export const fetchPositions = () =>
  api.get('/positions').then(r => r.data);

export const fetchPerformance = (days: number = 7) =>
  api.get('/performance/summary', { params: { days } }).then(r => r.data);

export const fetchAlerts = () =>
  api.get('/alerts', { params: { limit: 20, unacknowledged_only: true } }).then(r => r.data);

export const acknowledgeAlert = (alertId: string) =>
  api.post(`/alerts/${alertId}/acknowledge`).then(r => r.data);

export const fetchSystemHealth = () =>
  api.get('/system/health').then(r => r.data);

export default api;
