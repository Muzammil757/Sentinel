import React from 'react';
import { Icon } from '../core/Icon.jsx';

const MAP = {
  allowed:  { label: 'Allowed',  icon: 'check',          fg: 'var(--status-allowed-fg)',   bg: 'var(--status-allowed-bg)' },
  blocked:  { label: 'Blocked',  icon: 'shield-x',       fg: 'var(--status-blocked-fg)',   bg: 'var(--status-blocked-bg)' },
  escalated:{ label: 'Escalated',icon: 'arrow-up-right', fg: 'var(--status-escalated-fg)', bg: 'var(--status-escalated-bg)' },
  failed:   { label: 'Failed',   icon: 'triangle-alert', fg: 'var(--status-failed-fg)',    bg: 'var(--status-failed-bg)' },
  conflict: { label: 'Conflict', icon: 'git-compare',    fg: 'var(--status-conflict-fg)',  bg: 'var(--status-conflict-bg)' },
  pending:  { label: 'Pending',  icon: 'clock',          fg: 'var(--status-pending-fg)',   bg: 'var(--status-pending-bg)' },
  review:   { label: 'In review',icon: 'message-square', fg: 'var(--blue-700)',            bg: 'var(--blue-50)' },
};

export function StatusBadge({ status = 'pending', children, showIcon = true, size = 'md', style, ...rest }) {
  const s = MAP[status] || MAP.pending;
  const lg = size === 'lg';
  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 5,
        height: lg ? 24 : 20, padding: lg ? '0 9px' : '0 7px',
        borderRadius: 'var(--radius-3)', background: s.bg, color: s.fg,
        font: `var(--fw-medium) ${lg ? 'var(--fs-12)' : 'var(--fs-11)'}/1 var(--font-sans)`,
        letterSpacing: 'var(--ls-caps)', textTransform: 'uppercase', whiteSpace: 'nowrap', ...style,
      }}
      {...rest}
    >
      {showIcon ? <Icon name={s.icon} size={lg ? 13 : 12} /> : null}
      {children || s.label}
    </span>
  );
}
