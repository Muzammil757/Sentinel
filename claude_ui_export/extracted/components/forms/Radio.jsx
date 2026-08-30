import React from 'react';

export function Radio({ label, description, checked, disabled = false, name, value, onChange, style }) {
  return (
    <label style={{ display: 'flex', gap: 8, alignItems: description ? 'flex-start' : 'center', cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.45 : 1, ...style }}>
      <input type="radio" name={name} value={value} checked={!!checked} disabled={disabled} onChange={onChange} style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
      <span style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: 15, height: 15, flex: '0 0 auto', marginTop: description ? 2 : 0,
        borderRadius: 'var(--radius-pill)',
        border: `1px solid ${checked ? 'var(--accent)' : 'var(--border-emphasis)'}`,
        background: 'var(--bg-surface)', transition: 'var(--transition-control)',
      }}>
        {checked ? <span style={{ width: 7, height: 7, borderRadius: 'var(--radius-pill)', background: 'var(--accent)' }} /> : null}
      </span>
      <span style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        <span style={{ font: 'var(--type-body-sm)' }}>{label}</span>
        {description ? <span style={{ font: 'var(--type-caption)', color: 'var(--text-secondary)' }}>{description}</span> : null}
      </span>
    </label>
  );
}
