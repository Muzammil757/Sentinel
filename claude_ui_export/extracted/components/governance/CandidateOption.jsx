import React from 'react';
import { Icon } from '../core/Icon.jsx';

export function CandidateOption({ name, proposedBy, score, verdict = 'considered', rationale, selected = false, rank, style, ...rest }) {
  const [hover, setHover] = React.useState(false);
  const v = {
    chosen: { fg: 'var(--status-allowed-fg)', label: 'Chosen', icon: 'check' },
    rejected: { fg: 'var(--status-blocked-fg)', label: 'Rejected', icon: 'x' },
    considered: { fg: 'var(--text-tertiary)', label: 'Considered', icon: 'minus' },
  }[verdict];
  return (
    <div
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{
        display: 'grid', gridTemplateColumns: '20px minmax(0,1fr) 60px 92px', gap: 12, alignItems: 'start',
        padding: '10px 12px', borderBottom: '1px solid var(--border-hairline)',
        background: selected ? 'var(--bg-selected)' : hover ? 'var(--bg-hover)' : 'transparent',
        transition: 'var(--transition-control)', ...style,
      }}
      {...rest}
    >
      <span data-numeric style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)', paddingTop: 1 }}>{rank}</span>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
        <span style={{ font: 'var(--fw-medium) var(--fs-13)/1.3 var(--font-sans)' }}>{name}</span>
        {rationale ? <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)', textWrap: 'pretty' }}>{rationale}</span> : null}
        {proposedBy ? <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>proposed by {proposedBy}</span> : null}
      </div>
      <span data-numeric style={{ font: 'var(--fw-medium) var(--fs-13)/1.3 var(--font-mono)', textAlign: 'right' }}>{score}</span>
      <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'flex-end', gap: 5, font: 'var(--fw-medium) var(--fs-11)/1.3 var(--font-sans)', letterSpacing: 'var(--ls-caps)', textTransform: 'uppercase', color: v.fg }}>
        <Icon name={v.icon} size={12} />{v.label}
      </span>
    </div>
  );
}
