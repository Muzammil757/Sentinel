import React from 'react';
import { Icon } from './Icon.jsx';

export function Tag({ children, onRemove, icon, style, ...rest }) {
  const [hover, setHover] = React.useState(false);
  return (
    <span
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 5, height: 22, padding: '0 7px',
        borderRadius: 'var(--radius-3)', background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)',
        font: 'var(--type-mono)', letterSpacing: 'var(--ls-mono)',
        transition: 'var(--transition-control)',
        ...(hover ? { borderColor: 'var(--border-strong)', color: 'var(--text-primary)' } : null), ...style,
      }}
      {...rest}
    >
      {icon ? <Icon name={icon} size={12} /> : null}
      {children}
      {onRemove ? (
        <button type="button" onClick={onRemove} aria-label="Remove"
          style={{ display: 'inline-flex', border: 0, background: 'none', padding: 0, marginLeft: 1, cursor: 'pointer', color: 'var(--text-tertiary)' }}>
          <Icon name="x" size={11} />
        </button>
      ) : null}
    </span>
  );
}
