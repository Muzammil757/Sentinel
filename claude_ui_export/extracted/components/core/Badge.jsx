import React from 'react';

const TONES = {
  neutral: { bg: 'var(--bg-inset)', fg: 'var(--text-secondary)', bd: 'var(--border-subtle)' },
  accent: { bg: 'var(--blue-50)', fg: 'var(--blue-700)', bd: 'var(--blue-100)' },
  allowed: { bg: 'var(--status-allowed-bg)', fg: 'var(--status-allowed-fg)', bd: 'transparent' },
  escalated: { bg: 'var(--status-escalated-bg)', fg: 'var(--status-escalated-fg)', bd: 'transparent' },
  blocked: { bg: 'var(--status-blocked-bg)', fg: 'var(--status-blocked-fg)', bd: 'transparent' },
  conflict: { bg: 'var(--status-conflict-bg)', fg: 'var(--status-conflict-fg)', bd: 'transparent' },
};

export function Badge({ children, tone = 'neutral', mono = false, style, ...rest }) {
  const t = TONES[tone] || TONES.neutral;
  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center', height: 18, padding: '0 6px',
        borderRadius: 'var(--radius-3)', background: t.bg, color: t.fg,
        border: `1px solid ${t.bd}`,
        font: mono ? 'var(--type-label)' : 'var(--fw-medium) var(--fs-11)/1 var(--font-sans)',
        letterSpacing: mono ? 'var(--ls-label)' : 'var(--ls-caps)',
        textTransform: mono ? 'uppercase' : 'none', whiteSpace: 'nowrap', ...style,
      }}
      {...rest}
    >{children}</span>
  );
}
