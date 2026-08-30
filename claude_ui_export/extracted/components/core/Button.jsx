import React from 'react';
import { Icon } from './Icon.jsx';

const SIZES = {
  sm: { height: 26, padding: '0 8px', font: 'var(--fw-medium) var(--fs-12)/1 var(--font-sans)', gap: 6, icon: 13 },
  md: { height: 'var(--control-height)', padding: '0 12px', font: 'var(--fw-medium) var(--fs-13)/1 var(--font-sans)', gap: 6, icon: 14 },
  lg: { height: 'var(--control-height-lg)', padding: '0 16px', font: 'var(--fw-medium) var(--fs-14)/1 var(--font-sans)', gap: 8, icon: 16 },
};

const VARIANTS = {
  primary: { rest: { background: 'var(--accent)', color: 'var(--text-inverse)', border: '1px solid var(--accent)' },
             hover: { background: 'var(--accent-hover)', border: '1px solid var(--accent-hover)' },
             press: { background: 'var(--accent-press)', border: '1px solid var(--accent-press)' } },
  secondary: { rest: { background: 'var(--bg-surface)', color: 'var(--text-primary)', border: '1px solid var(--border-strong)', boxShadow: 'var(--shadow-1)' },
             hover: { background: 'var(--bg-hover)', border: '1px solid var(--ink-300)' },
             press: { background: 'var(--bg-active)' } },
  ghost: { rest: { background: 'transparent', color: 'var(--text-secondary)', border: '1px solid transparent' },
             hover: { background: 'var(--bg-hover)', color: 'var(--text-primary)' },
             press: { background: 'var(--bg-active)' } },
  danger: { rest: { background: 'var(--bg-surface)', color: 'var(--red-700)', border: '1px solid var(--red-100)' },
             hover: { background: 'var(--red-100)' },
             press: { background: 'var(--red-100)', color: 'var(--red-700)' } },
};

export function Button({
  children, variant = 'secondary', size = 'md', icon, trailingIcon,
  disabled = false, loading = false, fullWidth = false, style, ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const [press, setPress] = React.useState(false);
  const s = SIZES[size] || SIZES.md;
  const v = VARIANTS[variant] || VARIANTS.secondary;
  const state = disabled ? {} : press ? { ...v.hover, ...v.press } : hover ? v.hover : {};
  return (
    <button
      type="button"
      disabled={disabled || loading}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => { setHover(false); setPress(false); }}
      onMouseDown={() => setPress(true)}
      onMouseUp={() => setPress(false)}
      style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: fullWidth ? '100%' : 'auto',
        height: s.height, padding: s.padding, gap: s.gap, font: s.font,
        letterSpacing: 'var(--ls-body)', borderRadius: 'var(--radius-4)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.45 : 1,
        transition: 'var(--transition-control)',
        whiteSpace: 'nowrap',
        ...v.rest, ...state, ...style,
      }}
      {...rest}
    >
      {loading ? <Icon name="loader" size={s.icon} /> : icon ? <Icon name={icon} size={s.icon} /> : null}
      {children}
      {trailingIcon ? <Icon name={trailingIcon} size={s.icon} /> : null}
    </button>
  );
}
