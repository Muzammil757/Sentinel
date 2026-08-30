import React from 'react';

export function Tooltip({ label, side = 'top', children, style }) {
  const [open, setOpen] = React.useState(false);
  const pos = {
    top: { bottom: '100%', left: '50%', transform: 'translate(-50%,-6px)' },
    bottom: { top: '100%', left: '50%', transform: 'translate(-50%,6px)' },
    right: { left: '100%', top: '50%', transform: 'translate(6px,-50%)' },
    left: { right: '100%', top: '50%', transform: 'translate(-6px,-50%)' },
  }[side];
  return (
    <span
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      style={{ position: 'relative', display: 'inline-flex', ...style }}
    >
      {children}
      <span
        role="tooltip"
        style={{
          position: 'absolute', ...pos, zIndex: 40, pointerEvents: 'none',
          padding: '4px 7px', borderRadius: 'var(--radius-3)',
          background: 'var(--ink-900)', color: 'var(--text-inverse)',
          font: 'var(--fw-regular) var(--fs-12)/1.35 var(--font-sans)',
          maxWidth: 240, whiteSpace: 'nowrap',
          boxShadow: 'var(--shadow-2)',
          opacity: open ? 1 : 0,
          transition: `opacity var(--dur-fast) var(--ease-standard)`,
        }}
      >{label}</span>
    </span>
  );
}
