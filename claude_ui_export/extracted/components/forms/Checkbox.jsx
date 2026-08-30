import React from 'react';
import { Icon } from '../core/Icon.jsx';

export function Checkbox({ label, description, checked, indeterminate = false, disabled = false, onChange, style }) {
  const on = checked || indeterminate;
  return (
    <label style={{ display: 'flex', gap: 8, alignItems: description ? 'flex-start' : 'center', cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.45 : 1, ...style }}>
      <input type="checkbox" checked={!!checked} disabled={disabled} onChange={onChange} style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
      <span style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: 15, height: 15, flex: '0 0 auto', marginTop: description ? 2 : 0,
        borderRadius: 'var(--radius-3)',
        border: `1px solid ${on ? 'var(--accent)' : 'var(--border-emphasis)'}`,
        background: on ? 'var(--accent)' : 'var(--bg-surface)',
        color: 'var(--text-inverse)', transition: 'var(--transition-control)',
      }}>
        {indeterminate ? <Icon name="minus" size={11} /> : checked ? <Icon name="check" size={11} /> : null}
      </span>
      <span style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        <span style={{ font: 'var(--type-body-sm)' }}>{label}</span>
        {description ? <span style={{ font: 'var(--type-caption)', color: 'var(--text-secondary)' }}>{description}</span> : null}
      </span>
    </label>
  );
}
