import React from 'react';

const ACTOR_COLOR = {
  system: 'var(--text-inverse-secondary)', govern: '#7FA6F0', agent: '#B3A2E0',
  execution: '#7FCFA8', reviewer: '#E3C07B',
};

export function AuditTrail({ entries = [], style, ...rest }) {
  return (
    <ol
      style={{
        display: 'flex', flexDirection: 'column', gap: 0, margin: 0, padding: 0, listStyle: 'none',
        background: 'var(--bg-console)', color: 'var(--text-inverse)',
        borderRadius: 'var(--radius-4)', border: '1px solid var(--border-console)',
        font: 'var(--type-mono)', overflow: 'hidden', ...style,
      }}
      {...rest}
    >
      {entries.map((e, i) => (
        <li key={i} style={{ display: 'grid', gridTemplateColumns: '92px 84px minmax(0,1fr)', gap: 12, padding: '7px 12px', borderBottom: i === entries.length - 1 ? 0 : '1px solid rgba(255,255,255,.06)' }}>
          <span data-numeric style={{ color: 'var(--text-inverse-secondary)' }}>{e.time}</span>
          <span style={{ color: ACTOR_COLOR[e.actorKind] || 'var(--text-inverse-secondary)', textTransform: 'uppercase', letterSpacing: 'var(--ls-label)', fontSize: 'var(--fs-11)' }}>{e.actor}</span>
          <span style={{ color: 'rgba(255,255,255,.88)', textWrap: 'pretty' }}>
            {e.message}
            {e.detail ? <span style={{ color: 'var(--text-inverse-secondary)' }}>{'  '}{e.detail}</span> : null}
          </span>
        </li>
      ))}
    </ol>
  );
}
