import React from 'react';

export function Textarea({ label, hint, rows = 3, counter, value, style, wrapperStyle, ...rest }) {
  const [focus, setFocus] = React.useState(false);
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6, ...wrapperStyle }}>
      {label ? <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>{label}</span> : null}
      <textarea
        rows={rows} value={value}
        onFocus={() => setFocus(true)} onBlur={() => setFocus(false)}
        style={{
          resize: 'vertical', padding: '8px 9px', background: 'var(--bg-surface)',
          borderRadius: 'var(--radius-4)', border: `1px solid ${focus ? 'var(--accent)' : 'var(--border-strong)'}`,
          boxShadow: focus ? '0 0 0 3px var(--focus-ring)' : 'none', outline: 'none',
          font: 'var(--type-body-sm)', color: 'var(--text-primary)',
          transition: 'var(--transition-control)', ...style,
        }}
        {...rest}
      />
      {hint || counter ? (
        <span style={{ display: 'flex', justifyContent: 'space-between', font: 'var(--type-caption)', color: 'var(--text-tertiary)' }}>
          <span>{hint}</span>{counter ? <span data-numeric>{counter}</span> : null}
        </span>
      ) : null}
    </label>
  );
}
