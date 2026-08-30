import React from 'react';
import { StatusBadge } from '../status/StatusBadge.jsx';

export function DecisionSummary({ outcome = 'blocked', headline, policy, reasons = [], decidedAt, decidedBy = 'GOVERN', style, ...rest }) {
  const accent = {
    allowed: 'var(--status-allowed-dot)', blocked: 'var(--status-blocked-dot)',
    escalated: 'var(--status-escalated-dot)', failed: 'var(--status-failed-dot)',
  }[outcome] || 'var(--ink-300)';
  return (
    <div
      style={{
        display: 'flex', flexDirection: 'column', gap: 12,
        padding: '14px 16px', background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)', borderTop: `2px solid ${accent}`,
        borderRadius: 'var(--radius-4)', ...style,
      }}
      {...rest}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <StatusBadge status={outcome} size="lg" />
        <span style={{ font: 'var(--type-heading)', letterSpacing: 'var(--ls-heading)', textWrap: 'pretty' }}>{headline}</span>
      </div>
      {reasons.length ? (
        <ul style={{ display: 'flex', flexDirection: 'column', gap: 7, margin: 0, padding: 0, listStyle: 'none' }}>
          {reasons.map((r, i) => (
            <li key={i} style={{ display: 'grid', gridTemplateColumns: '78px minmax(0,1fr)', gap: 12, font: 'var(--type-body-sm)' }}>
              <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)', paddingTop: 3 }}>{r.label}</span>
              <span style={{ color: 'var(--text-primary)', textWrap: 'pretty' }}>{r.value}</span>
            </li>
          ))}
        </ul>
      ) : null}
      <div style={{ display: 'flex', gap: 14, paddingTop: 2, borderTop: '1px solid var(--border-hairline)', paddingTop: 10, font: 'var(--type-mono)', color: 'var(--text-tertiary)', flexWrap: 'wrap' }}>
        {policy ? <span>policy {policy}</span> : null}
        <span>decided by {decidedBy}</span>
        {decidedAt ? <span data-numeric>{decidedAt}</span> : null}
      </div>
    </div>
  );
}
