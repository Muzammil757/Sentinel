import React from 'react';

export function Panel({ title, label, actions, footer, padded = true, tone = 'surface', children, style, bodyStyle, ...rest }) {
  const dark = tone === 'console';
  return (
    <section
      style={{
        display: 'flex', flexDirection: 'column', minWidth: 0,
        background: dark ? 'var(--bg-console)' : tone === 'inset' ? 'var(--bg-inset)' : 'var(--bg-surface)',
        border: `1px solid ${dark ? 'var(--border-console)' : 'var(--border-subtle)'}`,
        borderRadius: 'var(--radius-6)', color: dark ? 'var(--text-inverse)' : 'inherit', ...style,
      }}
      {...rest}
    >
      {title || label || actions ? (
        <header style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
          minHeight: 40, padding: '0 12px 0 14px',
          borderBottom: `1px solid ${dark ? 'var(--border-console)' : 'var(--border-hairline)'}`,
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, minWidth: 0 }}>
            {label ? <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: dark ? 'var(--text-inverse-secondary)' : 'var(--text-tertiary)' }}>{label}</span> : null}
            {title ? <span style={{ font: 'var(--type-subheading)', letterSpacing: 'var(--ls-heading)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{title}</span> : null}
          </div>
          {actions ? <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>{actions}</div> : null}
        </header>
      ) : null}
      <div style={{ flex: 1, minWidth: 0, padding: padded ? 'var(--space-14, 14px)' : 0, ...bodyStyle }}>{children}</div>
      {footer ? (
        <footer style={{ padding: '10px 14px', borderTop: `1px solid ${dark ? 'var(--border-console)' : 'var(--border-hairline)'}`, font: 'var(--type-caption)', color: dark ? 'var(--text-inverse-secondary)' : 'var(--text-secondary)' }}>{footer}</footer>
      ) : null}
    </section>
  );
}
