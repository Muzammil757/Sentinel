import React from 'react';

export function ReliabilityMeter({ label, value, target, unit = '%', bars = 24, tone = 'allowed', style, ...rest }) {
  const pct = Math.max(0, Math.min(100, value));
  const filled = Math.round((pct / 100) * bars);
  const color = tone === 'blocked' ? 'var(--status-blocked-dot)' : tone === 'escalated' ? 'var(--status-escalated-dot)' : 'var(--status-allowed-dot)';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0, ...style }} {...rest}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 8 }}>
        <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>{label}</span>
        <span style={{ font: 'var(--fw-medium) var(--fs-13)/1 var(--font-mono)', fontVariantNumeric: 'tabular-nums' }}>{value}{unit}</span>
      </div>
      <div style={{ display: 'flex', gap: 2, alignItems: 'flex-end', height: 12 }}>
        {Array.from({ length: bars }).map((_, i) => (
          <span key={i} style={{ flex: 1, height: i < filled ? 12 : 6, background: i < filled ? color : 'var(--ink-150)', borderRadius: 1 }} />
        ))}
      </div>
      {target ? <span style={{ font: 'var(--type-caption)', color: 'var(--text-tertiary)' }}>{target}</span> : null}
    </div>
  );
}
