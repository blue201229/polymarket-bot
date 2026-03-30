import React from 'react';
import { useAlerts, useAcknowledgeAlert } from '../hooks/useAPI';

const severityColors: Record<string, string> = {
  info: 'var(--accent)',
  warning: 'var(--yellow)',
  critical: 'var(--red)',
};

export default function AlertsPage() {
  const { data, isLoading } = useAlerts({ limit: 50 });
  const ackMutation = useAcknowledgeAlert();

  if (isLoading) return <div className="loading">Loading alerts...</div>;

  const alerts = data?.alerts || [];

  return (
    <div>
      <div className="page-header">
        <h2>Alerts</h2>
        <p>System alerts, anomaly detections, and risk warnings</p>
      </div>

      {alerts.length === 0 ? (
        <div className="empty-state">
          <h3>No alerts</h3>
          <p>Everything is running smoothly.</p>
        </div>
      ) : (
        alerts.map((a: any) => (
          <div
            key={a.id}
            className="card"
            style={{
              borderLeft: `3px solid ${severityColors[a.severity] || 'var(--border)'}`,
              opacity: a.acknowledged ? 0.6 : 1,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span
                    className="tag"
                    style={{
                      background: `${severityColors[a.severity]}20`,
                      color: severityColors[a.severity],
                    }}
                  >
                    {a.severity?.toUpperCase()}
                  </span>
                  <span className="tag">{a.alert_type}</span>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {new Date(a.created_at).toLocaleString()}
                  </span>
                </div>
                <h4 style={{ fontSize: '15px', marginBottom: '4px' }}>{a.title}</h4>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{a.message}</p>
              </div>
              {!a.acknowledged && (
                <button
                  className="btn btn-secondary"
                  onClick={() => ackMutation.mutate(a.id)}
                  style={{ flexShrink: 0 }}
                >
                  Acknowledge
                </button>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
