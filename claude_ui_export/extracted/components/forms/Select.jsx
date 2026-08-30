import React from 'react';
import { Icon } from '../core/Icon.jsx';

export function Select({ label, options = [], hint, size = 'md', style, wrapperStyle, ...rest }) {
  const [focus, setFocus] = React.useState(false);
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6, ...wrapperStyle }}>
      {label ? <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>{label}</span> : null}
      <span style={{
        position: 'relative', display: 'flex', alignItems: 'center',
        height: size === 'lg' ? 'var(--control-height-lg)' : 'var(--control-height)',
        background: 'var(--bg-surface)', borderRadius: 'var(--radius-4)',
        border: `1px solid ${focus ? 'var(--accent)' : 'var(--border-strong)'}`,
        boxShadow: focus ? '0 0 0 3px var(--focus-ring)' : 'var(--shadow-1)',
        transition: 'var(--transition-control)',
      }}>
        <select
          onFocus={() => setFocus(true)} onBlur={() => setFocus(false)}
          style={{
            appearance: 'none', WebkitAppearance: 'none', border: 0, outline: 'none',
            background: 'none', padding: '0 26px 0 9px', width: '100%', height: '100%',
            font: 'var(--type-body-sm)', color: 'var(--text-primary)', cursor: 'pointer', ...style,
          }}
          {...rest}
        >
          {options.map((o) => {
            const v = typeof o === 'string' ? o : o.value;
            const l = typeof o === 'string' ? o : o.label;
            return <option key={v} value={v}>{l}</option>;
          })}
        </select>
        <Icon name="chevron-down" size={13} style={{ position: 'absolute', right: 8, color: 'var(--text-tertiary)', pointerEvents: 'none' }} />
      </span>
      {hint ? <span style={{ font: 'var(--type-caption)', color: 'var(--text-tertiary)' }}>{hint}</span> : null}
    </label>
  );
}
