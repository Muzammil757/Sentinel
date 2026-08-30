import React from 'react';
import { Icon } from '../core/Icon.jsx';
import { StatusBadge } from '../status/StatusBadge.jsx';

export function CaseRow({ id, title, status, agentConflict = false, surface, amount, time, selected = false, onClick, style, ...rest }) {
  const [hover, setHover] = React.useState(false);
  return (
    <div
      role="row" onClick={onClick}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{
        display: 'grid', gridTemplateColumns: '104px minmax(0,1fr) auto 96px 108px 68px',
        alignItems: 'center', gap: 12, height: 'var(--row-height)', padding: '0 14px',
        borderBottom: '1px solid var(--border-hairline)', cursor: 'pointer',
        background: selected ? 'var(--bg-selected)' : hover ? 'var(--bg-hover)' : 'transparent',
        boxShadow: selected ? 'inset 2px 0 0 var(--accent)' : 'none',
        transition: 'var(--transition-control)', ...style,
      }}
      {...rest}
    >
      <span style={{ font: 'var(--type-mono)', color: 'var(--text-secondary)' }}>{id}</span>
      <span style={{ display: 'flex', alignItems: 'center', gap: 7, minWidth: 0 }}>
        <span style={{ font: `${selected ? 'var(--fw-medium)' : 'var(--fw-regular)'} var(--fs-13)/1.3 var(--font-sans)`, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{title}</span>
        {agentConflict ? <Icon name="git-compare" size={13} style={{ color: 'var(--status-conflict-dot)' }} title="Agent disagreement" /> : null}
      </span>
      <StatusBadge status={status} />
      <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{surface}</span>
      <span data-numeric style={{ font: 'var(--type-mono)', fontSize: 'var(--fs-13)', textAlign: 'right' }}>{amount}</span>
      <span data-numeric style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)', textAlign: 'right' }}>{time}</span>
    </div>
  );
}
