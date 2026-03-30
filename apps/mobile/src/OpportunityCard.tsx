import type { MarketCandidate } from '../../../shared/contracts/platform';

type OpportunityCardProps = {
  candidate: MarketCandidate;
};

export function OpportunityCard({ candidate }: OpportunityCardProps) {
  return (
    <>
      <h2>{candidate.market.question}</h2>
      <p>Priority: {candidate.priority_score.toFixed(2)}</p>
      <p>AI: {candidate.ai_score ? `${candidate.ai_score.score.toFixed(1)}/10` : 'disabled'}</p>
      <p>{candidate.ai_score?.reasoning ?? 'Deterministic mode only'}</p>
    </>
  );
}
