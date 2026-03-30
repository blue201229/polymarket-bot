import React from 'react';
import { useWallets } from '../hooks/useAPI';
import AIScoreBadge from '../components/AIScoreBadge';

export default function WalletsPage() {
  const { data, isLoading } = useWallets();

  if (isLoading) return <div className="loading">Loading wallets...</div>;

  const wallets = data?.wallets || [];

  return (
    <div>
      <div className="page-header">
        <h2>Watched Wallets</h2>
        <p>Wallet monitoring with AI-powered quality analysis</p>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Address</th>
              <th>Label</th>
              <th>AI Quality</th>
              <th>Strategy</th>
              <th>Copy Enabled</th>
              <th>Total Trades</th>
              <th>Win Rate</th>
              <th>Analyzed</th>
            </tr>
          </thead>
          <tbody>
            {wallets.map((w: any) => (
              <tr key={w.address}>
                <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                  {w.address?.substring(0, 12)}...
                </td>
                <td>{w.label || '—'}</td>
                <td>
                  <AIScoreBadge score={w.ai_quality_score} />
                </td>
                <td>
                  {w.ai_strategy_class ? (
                    <span className="tag">{w.ai_strategy_class}</span>
                  ) : '—'}
                </td>
                <td>
                  {w.copy_enabled ? (
                    <span style={{ color: 'var(--green)' }}>Active</span>
                  ) : (
                    <span style={{ color: 'var(--text-muted)' }}>Off</span>
                  )}
                </td>
                <td>{w.total_trades}</td>
                <td>{w.win_rate ? `${w.win_rate.toFixed(1)}%` : '—'}</td>
                <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {w.ai_analyzed_at ? new Date(w.ai_analyzed_at).toLocaleDateString() : 'Never'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {wallets.length === 0 && (
          <div className="empty-state">
            <h3>No watched wallets</h3>
            <p>Add wallet addresses to track and analyze.</p>
          </div>
        )}
      </div>
    </div>
  );
}
