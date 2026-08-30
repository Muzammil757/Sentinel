import React from 'react';

const LINKS = ['Agents', 'Conflict', 'Resolve', 'Weigh', 'Govern', 'Executor'];

const TONE = {
  clear: { fg: 'var(--text-secondary)', mark: 'var(--border-emphasis)', fill: 'transparent' },
  passed: { fg: 'var(--text-primary)', mark: 'var(--status-allowed-dot)', fill: 'var(--status-allowed-dot)' },
  active: { fg: 'var(--text-primary)', mark: 'var(--accent)', fill: 'var(--accent)' },
  conflict: { fg: 'var(--status-conflict-fg)', mark: 'var(--status-conflict-dot)', fill: 'var(--status-conflict-dot)' },
  blocked: { fg: 'var(--status-blocked-fg)', mark: 'var(--status-blocked-dot)', fill: 'var(--status-blocked-dot)' },
  escalated: { fg: 'var(--status-escalated-fg)', mark: 'var(--status-escalated-dot)', fill: 'var(--status-escalated-dot)' },
  halted: { fg: 'var(--text-tertiary)', mark: 'var(--border-strong)', fill: 'transparent' },
  idle: { fg: 'var(--text-tertiary)', mark: 'var(--border-strong)', fill: 'transparent' },
};

export function CausalChain({ states = {}, size = 'md', showLabels = true, detail, style, ...rest }) {
  const compact = size === 'sm';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: compact ? 6 : 10, minWidth: 0, ...style }} {...rest}>
      {LINKS.map((link, i) => {
        const key = link.toLowerCase();
        const state = states[key] || 'idle';
        const t = TONE[state] || TONE.idle;
        const live = state === 'active';
        return (
          <React.Fragment key={link}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: compact ? 4 : 6, minWidth: 0 }}>
              <span style={{
                width: compact ? 5 : 7, height: compact ? 5 : 7, flex: '0 0 auto',
                borderRadius: 'var(--radius-pill)', background: t.fill,
                border: t.fill === 'transparent' ? `1px solid ${t.mark}` : 'none',
                boxShadow: live ? `0 0 0 3px color-mix(in oklab, ${t.mark} 20%, transparent)` : 'none',
              }} />
              {showLabels ? (
                <span style={{
                  font: `var(--fw-medium) ${compact ? 'var(--fs-10)' : 'var(--fs-11)'}/1 var(--font-mono)`,
                  letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: t.fg, whiteSpace: 'nowrap',
                }}>{link}</span>
              ) : null}
            </span>
            {i < LINKS.length - 1 ? (
              <span style={{ width: compact ? 10 : 18, height: 1, flex: compact ? '0 0 auto' : '1 1 auto', minWidth: 8, background: 'var(--border-subtle)' }} />
            ) : null}
          </React.Fragment>
        );
      })}
      {detail ? <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)', marginLeft: 6, whiteSpace: 'nowrap' }}>{detail}</span> : null}
    </div>
  );
}
