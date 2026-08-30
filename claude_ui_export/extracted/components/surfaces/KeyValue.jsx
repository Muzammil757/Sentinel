import React from 'react';

export function KeyValue({ items = [], columns = 1, dense = false, style, ...rest }) {
  return (
    <dl style={{ display: 'grid', gridTemplateColumns: `repeat(${columns}, minmax(0,1fr))`, gap: dense ? '6px 24px' : '10px 24px', margin: 0, ...style }} {...rest}>
      {items.map((it, i) => (
        <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
          <dt style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>{it.label}</dt>
          <dd style={{
            margin: 0, minWidth: 0,
            font: it.mono ? 'var(--type-mono)' : 'var(--type-body-sm)',
            fontSize: it.mono ? 'var(--fs-13)' : undefined,
            color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>{it.value}</dd>
        </div>
      ))}
    </dl>
  );
}
