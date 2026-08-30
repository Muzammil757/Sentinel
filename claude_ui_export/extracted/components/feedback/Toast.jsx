import React from 'react';
import { Icon } from '../core/Icon.jsx';
import { IconButton } from '../core/IconButton.jsx';

export function Toast({ tone = 'neutral', title, detail, onDismiss, style, ...rest }) {
  const accent = { neutral: 'var(--ink-300)', allowed: 'var(--status-allowed-dot)', blocked: 'var(--status-blocked-dot)', escalated: 'var(--status-escalated-dot)' }[tone];
  const icon = { neutral: 'info', allowed: 'check', blocked: 'shield-x', escalated: 'arrow-up-right' }[tone];
  return (
    <div
      style={{
        display: 'flex', alignItems: 'flex-start', gap: 9, minWidth: 300, maxWidth: 420,
        padding: '10px 10px 10px 12px', background: 'var(--bg-console)', color: 'var(--text-inverse)',
        border: '1px solid var(--border-console)', borderRadius: 'var(--radius-4)',
        boxShadow: 'var(--shadow-popover)', ...style,
      }}
      {...rest}
    >
      <Icon name={icon} size={14} style={{ color: accent, marginTop: 2 }} />
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
        <span style={{ font: 'var(--fw-medium) var(--fs-13)/1.3 var(--font-sans)' }}>{title}</span>
        {detail ? <span style={{ font: 'var(--type-mono)', color: 'var(--text-inverse-secondary)' }}>{detail}</span> : null}
      </div>
      {onDismiss ? <IconButton icon="x" size="sm" label="Dismiss" onClick={onDismiss} style={{ color: 'var(--text-inverse-secondary)' }} /> : null}
    </div>
  );
}
