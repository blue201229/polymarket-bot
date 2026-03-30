import type { MarketDiscoveryResponse } from '../../../shared/contracts/platform';

interface DashboardProps {
  response: MarketDiscoveryResponse;
  showAi: boolean;
}

export function MockDashboard({ response, showAi }: DashboardProps) {
  return (
    <section>
      <h1>Polymarket AI Platform</h1>
      <p>AI advisory mode: {response.ai_enabled ? 'enabled' : 'disabled'}</p>
      <table>
        <thead>
          <tr>
            <th>Market</th>
            <th>Deterministic</th>
            <th>AI score</th>
            <th>Priority</th>
          </tr>
        </thead>
        <tbody>
          {response.candidates.map((candidate) => (
            <tr key={candidate.market.market_id}>
              <td title={candidate.ai_score?.reasoning}>{candidate.market.question}</td>
              <td>{candidate.deterministic_priority.toFixed(2)}</td>
              <td>{showAi && candidate.ai_score ? candidate.ai_score.score.toFixed(2) : 'off'}</td>
              <td>{(showAi ? candidate.priority_score : candidate.deterministic_priority).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
