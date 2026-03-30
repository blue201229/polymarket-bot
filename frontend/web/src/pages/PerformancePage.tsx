import React from 'react';
import { usePerformance } from '../hooks/useAPI';
import StatCard from '../components/StatCard';

export default function PerformancePage() {
  const { data, isLoading } = usePerformance(7);

  if (isLoading) return <div className="loading">Loading performance data...</div>;

  if (!data) return null;

  const pnlVariant = (data.net_pnl || 0) >= 0 ? 'positive' : 'negative';

  return (
    <div>
      <div className="page-header">
        <h2>Performance</h2>
        <p>Trading performance metrics and strategy breakdown</p>
      </div>

      <div className="grid grid-4" style={{ marginBottom: '24px' }}>
        <StatCard label="Total Trades" value={data.total_trades} />
        <StatCard label="Win Rate" value={`${(data.win_rate || 0).toFixed(1)}%`} />
        <StatCard label="Net PnL" value={`$${(data.net_pnl || 0).toFixed(2)}`} variant={pnlVariant} />
        <StatCard label="Max Drawdown" value={`$${(data.max_drawdown || 0).toFixed(2)}`} variant="negative" />
      </div>

      <div className="grid grid-2" style={{ marginBottom: '24px' }}>
        <div className="card">
          <div className="card-header">
            <h3>Win/Loss</h3>
          </div>
          <div className="grid grid-2">
            <StatCard label="Wins" value={data.wins || 0} variant="positive" />
            <StatCard label="Losses" value={data.losses || 0} variant="negative" />
            <StatCard
              label="Avg Win"
              value={`$${(data.avg_win || 0).toFixed(2)}`}
              variant="positive"
            />
            <StatCard
              label="Avg Loss"
              value={`$${(data.avg_loss || 0).toFixed(2)}`}
              variant="negative"
            />
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Extremes</h3>
          </div>
          <div className="grid grid-2">
            <StatCard
              label="Best Trade"
              value={`$${(data.best_trade || 0).toFixed(2)}`}
              variant="positive"
            />
            <StatCard
              label="Worst Trade"
              value={`$${(data.worst_trade || 0).toFixed(2)}`}
              variant="negative"
            />
          </div>
        </div>
      </div>

      {/* Strategy Breakdown */}
      {data.strategies && Object.keys(data.strategies).length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3>Strategy Breakdown</h3>
          </div>
          <table>
            <thead>
              <tr>
                <th>Strategy</th>
                <th>Trades</th>
                <th>Win Rate</th>
                <th>PnL</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.strategies).map(([name, stats]: [string, any]) => (
                <tr key={name}>
                  <td><span className="tag">{name}</span></td>
                  <td>{stats.trades}</td>
                  <td>{stats.win_rate?.toFixed(1)}%</td>
                  <td style={{
                    color: stats.pnl >= 0 ? 'var(--green)' : 'var(--red)',
                    fontWeight: 600,
                  }}>
                    ${stats.pnl?.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
