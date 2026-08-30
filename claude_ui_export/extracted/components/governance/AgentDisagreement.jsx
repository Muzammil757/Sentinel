import React from 'react';
import { Icon } from '../core/Icon.jsx';

export function AgentDisagreement({ positions = [], subject, resolvedBy, style, ...rest }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, ...style }} {...rest}>
      {subject ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, font: 'var(--type-body-sm)', color: 'var(--text-secondary)' }}>
          <Icon name="git-compare" size={14} style={{ color: 'var(--status-conflict-dot)' }} />
          <span>{subject}</span>
        </div>
      ) : null}
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.max(positions.length, 1)}, minmax(0,1fr))`, gap: 1, background: 'var(--border-subtle)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-4)', overflow: 'hidden' }}>
        {positions.map((p, i) => (
          <div key={i} style={{ background: 'var(--bg-surface)', padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 5, minWidth: 0 }}>
            <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--status-conflict-fg)' }}>{p.agent}</span>
            <span style={{ font: 'var(--fw-medium) var(--fs-13)/1.35 var(--font-sans)', textWrap: 'pretty' }}>{p.position}</span>
            {p.basis ? <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)', textWrap: 'pretty' }}>{p.basis}</span> : null}
            {p.confidence != null ? <span data-numeric style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>confidence {p.confidence}</span> : null}
          </div>
        ))}
      </div>
      {resolvedBy ? (
        <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>resolved by {resolvedBy}</span>
      ) : null}
    </div>
  );
}
