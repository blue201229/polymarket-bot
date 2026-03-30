import React from 'react';

interface AIScoreBadgeProps {
  score: number | null;
  reasoning?: string | null;
}

export default function AIScoreBadge({ score, reasoning }: AIScoreBadgeProps) {
  if (score === null || score === undefined) {
    return <span className="ai-score low">N/A</span>;
  }

  const level = score >= 7 ? 'high' : score >= 4 ? 'medium' : 'low';

  if (reasoning) {
    return (
      <span className="tooltip">
        <span className={`ai-score ${level}`}>AI {score.toFixed(1)}</span>
        <span className="tooltip-text">{reasoning}</span>
      </span>
    );
  }

  return <span className={`ai-score ${level}`}>AI {score.toFixed(1)}</span>;
}
