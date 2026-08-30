import React from 'react';
import { Icon } from '../core/Icon.jsx';

const TONES = {
  info: { fg: 'var(--blue-700)', bg: 'var(--blue-50)', bd: 'var(--blue-100)', icon: 'info' },
  attention: { fg: 'var(--status-escalated-fg)', bg: 'var(--status-escalated-bg)', bd: 'transparent', icon: 'triangle-alert' },
  blocked: { fg: 'var(--status-blocked-fg)', bg: 'var(--status-blocked-bg)', bd: 'transparent', icon: 'shield-x' },
  neutral: { fg: 'var(--text-secondary)', bg: 'var(--bg-inset)', bd: 'var(--border-subtle)', icon: 'lock' },
};

export function InlineNotice({ tone = 'info', title, children, actions, icon, style, ...rest }) {
  const t = TONES[tone] || TONES.info;
  return (
    <div
      style={{
        display: 'flex', gap: 9, padding: '10px 12px', borderRadius: 'var(--radius-4)',
        background: t.bg, border: `1px solid ${t.bd}`, color: t.fg, ...style,
      }}
      {...rest}
    >
      <Icon name={icon || t.icon} size={15} style={{ marginTop: 1 }} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0, flex: 1 }}>
        {title ? <span style={{ font: 'var(--type-subheading)' }}>{title}</span> : null}
        <div style={{ font: 'var(--type-body-sm)', color: 'inherit', opacity: 0.92, textWrap: 'pretty' }}>{children}</div>
        {actions ? <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>{actions}</div> : null}
      </div>
    </div>
  );
}
