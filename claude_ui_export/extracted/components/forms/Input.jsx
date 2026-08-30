import React from 'react';
import { Icon } from '../core/Icon.jsx';

export function Input({ label, hint, error, icon, mono = false, size = 'md', style, wrapperStyle, ...rest }) {
  const [focus, setFocus] = React.useState(false);
  const h = size === 'lg' ? 'var(--control-height-lg)' : 'var(--control-height)';
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6, ...wrapperStyle }}>
      {label ? (
        <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>{label}</span>
      ) : null}
      <span style={{
        display: 'flex', alignItems: 'center', gap: 7, height: h, padding: '0 9px',
        background: 'var(--bg-surface)', borderRadius: 'var(--radius-4)',
        border: `1px solid ${error ? 'var(--red-600)' : focus ? 'var(--accent)' : 'var(--border-strong)'}`,
        boxShadow: focus ? `0 0 0 3px var(--focus-ring)` : 'none',
        transition: 'var(--transition-control)', color: 'var(--text-tertiary)',
      }}>
        {icon ? <Icon name={icon} size={14} /> : null}
        <input
          onFocus={() => setFocus(true)} onBlur={() => setFocus(false)}
          style={{
            flex: 1, minWidth: 0, border: 0, outline: 'none', background: 'none',
            font: mono ? 'var(--type-mono)' : 'var(--type-body-sm)',
            letterSpacing: mono ? 'var(--ls-mono)' : 'var(--ls-body)',
            color: 'var(--text-primary)', ...style,
          }}
          {...rest}
        />
      </span>
      {error || hint ? (
        <span style={{ font: 'var(--type-caption)', color: error ? 'var(--red-700)' : 'var(--text-tertiary)' }}>{error || hint}</span>
      ) : null}
    </label>
  );
}
