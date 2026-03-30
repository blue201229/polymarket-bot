import React from 'react';
import { usePositions } from '../hooks/useAPI';
import StatCard from '../components/StatCard';

export default function PositionsPage() {
  const { data, isLoading } = usePositions();

  if (isLoading) return <div className="loading">Loading positions...</div>;

  const positions = data?.positions || [];
  const totalUnrealized = data?.total_unrealized_pnl || 0;
  const totalRealized = data?.total_realized_pnl || 0;

  return (
    <div>
      <div className="page-header">
        <h2>Positions</h2>
        <p>Open positions and PnL tracking</p>
      </div>

      <div className="grid grid-3" style={{ marginBottom: '24px' }}>
        <StatCard label="Open Positions" value={data?.open_count || 0} />
        <StatCard
          label="Unrealized PnL"
          value={`$${totalUnrealized.toFixed(2)}`}
          variant={totalUnrealized >= 0 ? 'positive' : 'negative'}
        />
        <StatCard
          label="Realized PnL"
          value={`$${totalRealized.toFixed(2)}`}
          variant={totalRealized >= 0 ? 'positive' : 'negative'}
        />
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Outcome</th>
              <th>Side</th>
              <th>Size</th>
              <th>Entry Price</th>
              <th>Current Price</th>
              <th>Unrealized PnL</th>
              <th>Strategy</th>
              <th>Type</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p: any) => {
              const pnl = p.unrealized_pnl || 0;
              return (
                <tr key={p.id}>
                  <td>{p.outcome?.substring(0, 30)}</td>
                  <td style={{ color: p.side === 'buy' ? 'var(--green)' : 'var(--red)' }}>
                    {p.side?.toUpperCase()}
                  </td>
                  <td>{p.size?.toFixed(2)}</td>
                  <td>{p.avg_entry_price?.toFixed(3)}</td>
                  <td>{p.current_price?.toFixed(3)}</td>
                  <td style={{ color: pnl >= 0 ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
                    ${pnl.toFixed(2)}
                  </td>
                  <td><span className="tag">{p.strategy}</span></td>
                  <td>{p.is_paper ? '📝 Paper' : '🔴 Live'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {positions.length === 0 && (
          <div className="empty-state">
            <h3>No open positions</h3>
            <p>Positions will appear here once trades are executed.</p>
          </div>
        )}
      </div>
    </div>
  );
}
