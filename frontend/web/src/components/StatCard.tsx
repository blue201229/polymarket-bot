import React from 'react';

interface StatCardProps {
  label: string;
  value: string | number;
  variant?: 'default' | 'positive' | 'negative';
}

export default function StatCard({ label, value, variant = 'default' }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="label">{label}</div>
      <div className={`value ${variant}`}>{value}</div>
    </div>
  );
}
