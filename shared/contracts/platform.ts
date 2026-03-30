export type AIScoreSource = 'ai' | 'fallback' | 'disabled';

export interface AIScore {
  source: AIScoreSource;
  score: number;
  reasoning: string;
  tags: string[];
  latency_ms: number;
  decision_impact: string;
}

export interface HardFilterDecision {
  passed: boolean;
  reasons: string[];
  deterministic_score: number;
}

export interface MarketSnapshot {
  market_id: string;
  question: string;
  category: string;
  liquidity: number;
  volume_24h: number;
  spread_bps: number;
  resolution_clarity: number;
  end_time: string;
  metadata: Record<string, unknown>;
}

export interface MarketCandidate {
  market: MarketSnapshot;
  hard_filter: HardFilterDecision;
  deterministic_priority: number;
  ai_score?: AIScore;
  priority_score: number;
}

export interface MarketDiscoveryResponse {
  generated_at: string;
  ai_enabled: boolean;
  comparison_mode_available: boolean;
  candidates: MarketCandidate[];
}
