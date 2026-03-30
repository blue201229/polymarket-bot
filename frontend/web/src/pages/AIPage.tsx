import React, { useState } from 'react';
import { useAIImpact, useOptimize, usePostTradeAnalysis } from '../hooks/useAPI';
import StatCard from '../components/StatCard';

export default function AIPage() {
  const { data: impact } = useAIImpact(30);
  const optimizeMutation = useOptimize();
  const analysisMutation = usePostTradeAnalysis();
  const [optimizeResult, setOptimizeResult] = useState<any>(null);
  const [analysisResult, setAnalysisResult] = useState<any>(null);

  const handleOptimize = async () => {
    const result = await optimizeMutation.mutateAsync(7);
    setOptimizeResult(result);
  };

  const handleAnalysis = async () => {
    const result = await analysisMutation.mutateAsync(7);
    setAnalysisResult(result);
  };

  return (
    <div>
      <div className="page-header">
        <h2>AI Insights</h2>
        <p>AI performance impact, optimization suggestions, and trade analysis</p>
      </div>

      {/* AI Impact Comparison */}
      {impact && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header">
            <h3>AI vs Non-AI Performance ({impact.window_days} days)</h3>
          </div>
          <div className="grid grid-2">
            <div>
              <h4 style={{ color: 'var(--accent)', marginBottom: '12px' }}>AI-Assisted Trades</h4>
              <div className="grid grid-2">
                <StatCard label="Count" value={impact.ai_assisted?.count || 0} />
                <StatCard
                  label="Win Rate"
                  value={`${(impact.ai_assisted?.win_rate || 0).toFixed(1)}%`}
                />
                <StatCard
                  label="Avg PnL"
                  value={`$${(impact.ai_assisted?.avg_pnl || 0).toFixed(2)}`}
                  variant={(impact.ai_assisted?.avg_pnl || 0) >= 0 ? 'positive' : 'negative'}
                />
                <StatCard
                  label="Total PnL"
                  value={`$${(impact.ai_assisted?.total_pnl || 0).toFixed(2)}`}
                  variant={(impact.ai_assisted?.total_pnl || 0) >= 0 ? 'positive' : 'negative'}
                />
              </div>
            </div>
            <div>
              <h4 style={{ color: 'var(--text-secondary)', marginBottom: '12px' }}>Non-AI Trades</h4>
              <div className="grid grid-2">
                <StatCard label="Count" value={impact.non_ai?.count || 0} />
                <StatCard
                  label="Win Rate"
                  value={`${(impact.non_ai?.win_rate || 0).toFixed(1)}%`}
                />
                <StatCard
                  label="Avg PnL"
                  value={`$${(impact.non_ai?.avg_pnl || 0).toFixed(2)}`}
                  variant={(impact.non_ai?.avg_pnl || 0) >= 0 ? 'positive' : 'negative'}
                />
                <StatCard
                  label="Total PnL"
                  value={`$${(impact.non_ai?.total_pnl || 0).toFixed(2)}`}
                  variant={(impact.non_ai?.total_pnl || 0) >= 0 ? 'positive' : 'negative'}
                />
              </div>
            </div>
          </div>
          <div style={{ marginTop: '12px', color: 'var(--text-secondary)', fontSize: '13px' }}>
            AI skipped {impact.ai_skip_count || 0} trades
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="grid grid-2" style={{ marginBottom: '24px' }}>
        <div className="card">
          <div className="card-header">
            <h3>Parameter Optimization</h3>
            <button
              className="btn btn-primary"
              onClick={handleOptimize}
              disabled={optimizeMutation.isPending}
            >
              {optimizeMutation.isPending ? 'Running...' : 'Run Optimization'}
            </button>
          </div>
          {optimizeResult && (
            <div>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                Confidence: {(optimizeResult.confidence * 100).toFixed(0)}%
                {' | Risk: '}{optimizeResult.risk_level}
              </p>
              {optimizeResult.suggestions?.map((s: any, i: number) => (
                <div key={i} style={{
                  padding: '8px 12px',
                  background: 'var(--bg-tertiary)',
                  borderRadius: 'var(--radius)',
                  marginBottom: '8px',
                  fontSize: '13px',
                }}>
                  <strong>{s.parameter}</strong>: {s.current_value} → {s.suggested_value}
                  <br />
                  <span style={{ color: 'var(--text-secondary)' }}>{s.reasoning}</span>
                </div>
              ))}
              <p style={{ fontSize: '13px', marginTop: '12px' }}>{optimizeResult.overall_assessment}</p>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Post-Trade Analysis</h3>
            <button
              className="btn btn-primary"
              onClick={handleAnalysis}
              disabled={analysisMutation.isPending}
            >
              {analysisMutation.isPending ? 'Analyzing...' : 'Run Analysis'}
            </button>
          </div>
          {analysisResult && (
            <div>
              {analysisResult.top_improvement && (
                <div style={{
                  padding: '12px',
                  background: 'rgba(91, 108, 247, 0.1)',
                  borderRadius: 'var(--radius)',
                  marginBottom: '12px',
                  fontSize: '13px',
                  borderLeft: '3px solid var(--accent)',
                }}>
                  <strong>Top Improvement:</strong> {analysisResult.top_improvement}
                </div>
              )}
              {analysisResult.insights?.map((insight: any, i: number) => (
                <div key={i} style={{
                  padding: '8px 12px',
                  background: 'var(--bg-tertiary)',
                  borderRadius: 'var(--radius)',
                  marginBottom: '8px',
                  fontSize: '13px',
                }}>
                  <span className="tag">{insight.category}</span>
                  <p style={{ marginTop: '4px' }}>{insight.finding}</p>
                  <p style={{ color: 'var(--text-secondary)' }}>{insight.suggestion}</p>
                </div>
              ))}
              <p style={{ fontSize: '13px', marginTop: '12px' }}>{analysisResult.overall_assessment}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
