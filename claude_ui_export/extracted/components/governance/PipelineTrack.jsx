import React from 'react';
import { Icon } from '../core/Icon.jsx';

const STATE = {
  done:    { fg: 'var(--text-primary)',            mark: 'var(--status-allowed-dot)',   icon: 'check' },
  active:  { fg: 'var(--text-primary)',            mark: 'var(--accent)',               icon: 'dot' },
  blocked: { fg: 'var(--status-blocked-fg)',       mark: 'var(--status-blocked-dot)',   icon: 'x' },
  halted:  { fg: 'var(--status-escalated-fg)',     mark: 'var(--status-escalated-dot)', icon: 'pause' },
  skipped: { fg: 'var(--text-tertiary)',           mark: 'var(--ink-200)',              icon: 'minus' },
  pending: { fg: 'var(--text-tertiary)',           mark: 'var(--ink-200)',              icon: 'dot' },
};

export function PipelineTrack({ stages = [], orientation = 'horizontal', style, ...rest }) {
  const vertical = orientation === 'vertical';
  return (
    <ol
      style={{
        display: 'flex', flexDirection: vertical ? 'column' : 'row', alignItems: vertical ? 'stretch' : 'stretch',
        gap: 0, margin: 0, padding: 0, listStyle: 'none', minWidth: 0, ...style,
      }}
      {...rest}
    >
      {stages.map((s, i) => {
        const st = STATE[s.state] || STATE.pending;
        const last = i === stages.length - 1;
        return (
          <li key={s.label} style={{ display: 'flex', flexDirection: vertical ? 'row' : 'column', gap: vertical ? 10 : 0, flex: vertical ? 'none' : 1, minWidth: 0, paddingBottom: vertical && !last ? 14 : 0 }}>
            <div style={{ display: 'flex', flexDirection: vertical ? 'column' : 'row', alignItems: 'center', gap: 0, flex: '0 0 auto' }}>
              <span style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                width: 16, height: 16, borderRadius: 'var(--radius-pill)', flex: '0 0 auto',
                background: s.state === 'pending' || s.state === 'skipped' ? 'transparent' : st.mark,
                border: `1px solid ${s.state === 'pending' || s.state === 'skipped' ? 'var(--border-strong)' : st.mark}`,
                color: 'var(--white)',
              }}>
                {s.state === 'done' ? <Icon name="check" size={10} /> : s.state === 'blocked' ? <Icon name="x" size={10} /> : s.state === 'active' ? <span style={{ width: 5, height: 5, borderRadius: 99, background: '#fff' }} /> : null}
              </span>
              {!last ? (
                <span style={{
                  flex: vertical ? '0 0 auto' : 1, alignSelf: 'stretch',
                  width: vertical ? 1 : 'auto', minHeight: vertical ? 18 : 0, height: vertical ? '100%' : 1,
                  margin: vertical ? '4px 0 0 7px' : '0 6px', background: 'var(--border-strong)',
                }} />
              ) : null}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2, paddingTop: vertical ? 0 : 8, minWidth: 0 }}>
              <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: st.fg }}>{s.label}</span>
              {s.detail ? <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.detail}</span> : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
