import React from 'react';
import { Icon } from './Icon.jsx';

const BOX = { sm: 24, md: 30, lg: 36 };
const GLYPH = { sm: 14, md: 16, lg: 18 };

export function IconButton({ icon, size = 'md', variant = 'ghost', active = false, disabled = false, label, style, ...rest }) {
  const [hover, setHover] = React.useState(false);
  const box = BOX[size] || BOX.md;
  const bordered = variant === 'outline';
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: box, height: box, borderRadius: 'var(--radius-4)',
        border: bordered ? '1px solid var(--border-strong)' : '1px solid transparent',
        background: active ? 'var(--bg-active)' : hover && !disabled ? 'var(--bg-hover)' : bordered ? 'var(--bg-surface)' : 'transparent',
        color: active ? 'var(--text-primary)' : hover && !disabled ? 'var(--text-primary)' : 'var(--text-secondary)',
        cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.4 : 1,
        transition: 'var(--transition-control)', ...style,
      }}
      {...rest}
    >
      <Icon name={icon} size={GLYPH[size] || 16} />
    </button>
  );
}
