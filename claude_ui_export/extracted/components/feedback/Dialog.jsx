import React from 'react';
import { IconButton } from '../core/IconButton.jsx';

export function Dialog({ open = true, title, label, description, footer, width = 480, onClose, children, style }) {
  if (!open) return null;
  return (
    <div style={{ position: 'absolute', inset: 0, zIndex: 60, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--overlay-scrim)', backdropFilter: 'var(--blur-scrim)' }}>
      <div
        role="dialog" aria-modal="true"
        style={{
          width, maxWidth: '92%', background: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-6)',
          boxShadow: 'var(--shadow-popover)', display: 'flex', flexDirection: 'column', ...style,
        }}
      >
        <header style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '14px 12px 12px 16px', borderBottom: '1px solid var(--border-hairline)' }}>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 3 }}>
            {label ? <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>{label}</span> : null}
            <span style={{ font: 'var(--type-heading)', letterSpacing: 'var(--ls-heading)' }}>{title}</span>
            {description ? <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)', textWrap: 'pretty' }}>{description}</span> : null}
          </div>
          {onClose ? <IconButton icon="x" size="sm" label="Close" onClick={onClose} /> : null}
        </header>
        {children ? <div style={{ padding: 16 }}>{children}</div> : null}
        {footer ? <footer style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, padding: '12px 16px', borderTop: '1px solid var(--border-hairline)', background: 'var(--bg-inset)', borderRadius: '0 0 var(--radius-6) var(--radius-6)' }}>{footer}</footer> : null}
      </div>
    </div>
  );
}
