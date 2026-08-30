import React from 'react';

export function Tabs({ items = [], value, onChange, style, ...rest }) {
  return (
    <div role="tablist" style={{ display: 'flex', alignItems: 'stretch', gap: 2, borderBottom: '1px solid var(--border-subtle)', ...style }} {...rest}>
      {items.map((it) => {
        const id = typeof it === 'string' ? it : it.value;
        const label = typeof it === 'string' ? it : it.label;
        const count = typeof it === 'string' ? null : it.count;
        const active = value === id;
        return (
          <button
            key={id} role="tab" aria-selected={active} onClick={() => onChange && onChange(id)}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6, height: 34, padding: '0 10px',
              border: 0, background: 'none', cursor: 'pointer',
              font: `var(--fw-medium) var(--fs-13)/1 var(--font-sans)`,
              color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
              boxShadow: active ? 'inset 0 -2px 0 var(--ink-900)' : 'none',
              transition: 'var(--transition-control)',
            }}
          >
            {label}
            {count != null ? (
              <span data-numeric style={{ font: 'var(--type-mono)', fontSize: 'var(--fs-11)', color: active ? 'var(--text-secondary)' : 'var(--text-tertiary)' }}>{count}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
