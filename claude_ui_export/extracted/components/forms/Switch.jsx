import React from 'react';

export function Switch({ checked = false, disabled = false, label, onChange, style }) {
  return (
    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.45 : 1, ...style }}>
      <button
        type="button" role="switch" aria-checked={checked} disabled={disabled}
        onClick={onChange}
        style={{
          position: 'relative', width: 30, height: 17, flex: '0 0 auto', padding: 0,
          borderRadius: 'var(--radius-pill)', cursor: 'inherit',
          border: `1px solid ${checked ? 'var(--accent)' : 'var(--border-emphasis)'}`,
          background: checked ? 'var(--accent)' : 'var(--bg-inset)',
          transition: 'var(--transition-control)',
        }}
      >
        <span style={{
          position: 'absolute', top: 2, left: checked ? 15 : 2, width: 11, height: 11,
          borderRadius: 'var(--radius-pill)', background: 'var(--white)',
          boxShadow: '0 1px 1px rgba(11,14,19,.2)',
          transition: `left var(--dur-fast) var(--ease-standard)`,
        }} />
      </button>
      {label ? <span style={{ font: 'var(--type-body-sm)' }}>{label}</span> : null}
    </label>
  );
}
