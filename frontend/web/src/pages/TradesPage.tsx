import React from 'react';
import { useTrades, useTradeStats } from '../hooks/useAPI';
import StatCard from '../components/StatCard';

export default function TradesPage() {
  const { data, isLoading } = useTrades({ limit: 50 });
  const { data: stats } = useTradeStats();

  if (isLoading) return <div className="loading">Loading trades...</div>;

  const trades = data?.trades || [];

  return (
    <div>
      <div className="page-header">
        <h2>Trades</h2>
        <p>Recent trade history with AI confidence scores</p>
      </div>

      {stats && (
        <div className="grid grid-4" style={{ marginBottom: '24px' }}>
          <StatCard label="Total Trades" value={stats.total_trades} />
          <StatCard label="Filled" value={stats.filled_trades} />
          <StatCard label="Cancelled" value={stats.cancelled_trades} />
          <StatCard
            label="Total PnL"
            value={`$${stats.total_pnl?.toFixed(2)}`}
            variant={stats.total_pnl >= 0 ? 'positive' : 'negative'}
          />
        </div>
      )}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Outcome</th>
              <th>Side</th>
              <th>Price</th>
              <th>Size</th>
              <th>Strategy</th>
              <th>Status</th>
              <th>AI Confidence</th>
              <th>PnL</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t: any) => (
              <tr key={t.id}>
                <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {new Date(t.created_at).toLocaleString()}
                </td>
                <td>{t.outcome?.substring(0, 25)}</td>
                <td style={{ color: t.side === 'buy' ? 'var(--green)' : 'var(--red)' }}>
                  {t.side?.toUpperCase()}
                </td>
                <td>{t.price?.toFixed(3)}</td>
                <td>${t.size?.toFixed(2)}</td>
                <td><span className="tag">{t.strategy}</span></td>
                <td>
                  <span className={`status-badge ${t.status}`}>{t.status}</span>
                </td>
                <td>
                  {t.ai_confidence !== null ? (
                    <span style={{
                      color: t.ai_confidence >= 0.7 ? 'var(--green)' :
                             t.ai_confidence >= 0.4 ? 'var(--yellow)' : 'var(--red)',
                    }}>
                      {(t.ai_confidence * 100).toFixed(0)}%
                    </span>
                  ) : (
                    <span style={{ color: 'var(--text-muted)' }}>—</span>
                  )}
                </td>
                <td>
                  {t.pnl !== null ? (
                    <span style={{ color: t.pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                      ${t.pnl?.toFixed(2)}
                    </span>
                  ) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
