import React from 'react';

const DOT = {
  allowed: 'var(--status-allowed-dot)', blocked: 'var(--status-blocked-dot)',
  escalated: 'var(--status-escalated-dot)', failed: 'var(--status-failed-dot)',
  conflict: 'var(--status-conflict-dot)', pending: 'var(--status-pending-dot)',
};

export function SeverityDot({ status = 'pending', label, pulse = false, size = 7, style, ...rest }) {
  const color = DOT[status] || DOT.pending;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, ...style }} {...rest}>
      <span style={{
        width: size, height: size, borderRadius: 'var(--radius-pill)', background: color, flex: '0 0 auto',
        boxShadow: pulse ? `0 0 0 3px color-mix(in oklab, ${color} 22%, transparent)` : 'none',
      }} />
      {label ? <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)' }}>{label}</span> : null}
    </span>
  );
}
