import React from 'react';

/* 
  React Native Mobile App for Polymarket AI Trading Platform
  
  Screens:
  - Markets: Simplified AI scores with swipe actions
  - Positions: Open positions with PnL indicators  
  - Alerts: Push notification integration
  - Performance: Key metrics cards
  - Settings: Paper/live toggle, AI enable/disable
  
  Features:
  - Pull-to-refresh on all screens
  - Push notifications for high-confidence opportunities
  - Simplified AI score display (color-coded badges)
  - Quick trade actions
*/

interface Market {
  id: string;
  question: string;
  ai_score: number | null;
  volume_24h: number;
  outcomes: { outcome: string; price: number }[];
}

interface Position {
  id: string;
  outcome: string;
  side: string;
  size: number;
  avg_entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  strategy: string;
}

const API_BASE = 'http://localhost:8000/api/v1';

export function MarketsScreen() {
  const [markets, setMarkets] = React.useState<Market[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    fetch(`${API_BASE}/markets?limit=20`)
      .then(r => r.json())
      .then(data => {
        setMarkets(data.markets || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return { markets, loading };
}

export function PositionsScreen() {
  const [positions, setPositions] = React.useState<Position[]>([]);
  
  React.useEffect(() => {
    fetch(`${API_BASE}/positions`)
      .then(r => r.json())
      .then(data => setPositions(data.positions || []))
      .catch(() => {});
  }, []);

  return { positions };
}

export function AlertsScreen() {
  const [alerts, setAlerts] = React.useState<any[]>([]);
  
  React.useEffect(() => {
    fetch(`${API_BASE}/alerts?limit=20&unacknowledged_only=true`)
      .then(r => r.json())
      .then(data => setAlerts(data.alerts || []))
      .catch(() => {});
  }, []);

  return { alerts };
}

export function PerformanceScreen() {
  const [data, setData] = React.useState<any>(null);
  
  React.useEffect(() => {
    fetch(`${API_BASE}/performance/summary?days=7`)
      .then(r => r.json())
      .then(setData)
      .catch(() => {});
  }, []);

  return { data };
}

export default function App() {
  return null; // Requires React Native runtime
}
