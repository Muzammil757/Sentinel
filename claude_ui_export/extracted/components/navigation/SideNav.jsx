import React from 'react';
import { Icon } from '../core/Icon.jsx';

function Item({ item, active, onSelect }) {
  const [hover, setHover] = React.useState(false);
  return (
    <button
      type="button"
      onClick={() => onSelect && onSelect(item.value)}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{
        display: 'flex', alignItems: 'center', gap: 9, width: '100%', height: 30,
        padding: '0 8px', border: 0, borderRadius: 'var(--radius-4)', cursor: 'pointer',
        background: active ? 'var(--bg-active)' : hover ? 'var(--bg-hover)' : 'transparent',
        color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
        font: `${active ? 'var(--fw-medium)' : 'var(--fw-regular)'} var(--fs-13)/1 var(--font-sans)`,
        transition: 'var(--transition-control)', textAlign: 'left',
      }}
    >
      <Icon name={item.icon} size={15} style={{ color: active ? 'var(--text-primary)' : 'var(--text-tertiary)' }} />
      <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.label}</span>
      {item.count != null ? (
        <span data-numeric style={{ font: 'var(--type-mono)', fontSize: 'var(--fs-11)', color: item.attention ? 'var(--status-escalated-fg)' : 'var(--text-tertiary)' }}>{item.count}</span>
      ) : null}
    </button>
  );
}

export function SideNav({ sections = [], value, onSelect, header, footer, style, ...rest }) {
  return (
    <nav
      style={{
        display: 'flex', flexDirection: 'column', width: 'var(--sidebar-width)', flex: '0 0 auto',
        background: 'var(--bg-surface)', borderRight: '1px solid var(--border-subtle)', ...style,
      }}
      {...rest}
    >
      {header ? <div style={{ padding: '12px 12px 8px' }}>{header}</div> : null}
      <div style={{ flex: 1, overflow: 'auto', padding: '4px 8px 12px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        {sections.map((sec, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {sec.label ? (
              <div style={{ padding: '6px 8px 4px', font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>{sec.label}</div>
            ) : null}
            {sec.items.map((it) => <Item key={it.value} item={it} active={value === it.value} onSelect={onSelect} />)}
          </div>
        ))}
      </div>
      {footer ? <div style={{ padding: 12, borderTop: '1px solid var(--border-hairline)' }}>{footer}</div> : null}
    </nav>
  );
}
