import React from 'react';
import { useMarkets } from '../hooks/useAPI';
import AIScoreBadge from '../components/AIScoreBadge';

export default function MarketsPage() {
  const { data, isLoading } = useMarkets({ limit: 50 });

  if (isLoading) return <div className="loading">Loading markets...</div>;

  const markets = data?.markets || [];

  return (
    <div>
      <div className="page-header">
        <h2>Markets</h2>
        <p>AI-scored prediction markets ranked by opportunity quality</p>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Market</th>
              <th>AI Score</th>
              <th>Prices</th>
              <th>24h Volume</th>
              <th>Liquidity</th>
              <th>Tags</th>
            </tr>
          </thead>
          <tbody>
            {markets.map((m: any) => (
              <tr key={m.id}>
                <td>
                  <a
                    href={m.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: 'var(--text-primary)', textDecoration: 'none' }}
                  >
                    {m.question?.substring(0, 70)}
                    {m.question?.length > 70 ? '...' : ''}
                  </a>
                </td>
                <td>
                  <AIScoreBadge score={m.ai_score} reasoning={m.ai_reasoning} />
                </td>
                <td>
                  {m.outcomes?.map((o: any) => (
                    <div key={o.token_id} style={{ fontSize: '13px' }}>
                      {o.outcome}: {o.price.toFixed(3)}
                    </div>
                  ))}
                </td>
                <td>${(m.volume_24h || 0).toLocaleString()}</td>
                <td>${(m.liquidity || 0).toLocaleString()}</td>
                <td>
                  {m.ai_tags?.slice(0, 3).map((tag: string) => (
                    <span key={tag} className="tag">{tag}</span>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {markets.length === 0 && (
          <div className="empty-state">
            <h3>No markets found</h3>
            <p>Run market discovery to populate markets.</p>
          </div>
        )}
      </div>
    </div>
  );
}
