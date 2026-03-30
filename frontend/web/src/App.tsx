import React from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import MarketsPage from './pages/MarketsPage';
import TradesPage from './pages/TradesPage';
import PositionsPage from './pages/PositionsPage';
import WalletsPage from './pages/WalletsPage';
import AIPage from './pages/AIPage';
import PerformancePage from './pages/PerformancePage';
import AlertsPage from './pages/AlertsPage';

const navItems = [
  { path: '/', label: 'Markets' },
  { path: '/trades', label: 'Trades' },
  { path: '/positions', label: 'Positions' },
  { path: '/wallets', label: 'Wallets' },
  { path: '/ai', label: 'AI Insights' },
  { path: '/performance', label: 'Performance' },
  { path: '/alerts', label: 'Alerts' },
];

export default function App() {
  return (
    <div className="app">
      <nav className="sidebar">
        <div className="logo">
          <h1>Polymarket AI</h1>
          <span className="badge">Platform</span>
        </div>
        <ul className="nav-list">
          {navItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                end={item.path === '/'}
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <main className="content">
        <Routes>
          <Route path="/" element={<MarketsPage />} />
          <Route path="/trades" element={<TradesPage />} />
          <Route path="/positions" element={<PositionsPage />} />
          <Route path="/wallets" element={<WalletsPage />} />
          <Route path="/ai" element={<AIPage />} />
          <Route path="/performance" element={<PerformancePage />} />
          <Route path="/alerts" element={<AlertsPage />} />
        </Routes>
      </main>
    </div>
  );
}
