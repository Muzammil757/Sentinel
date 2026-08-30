import React from 'react';

export function SectionHeader({ title, meta, description, actions, size = 'md', style, ...rest }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, paddingBottom: 10, borderBottom: '1px solid var(--border-hairline)', ...style }} {...rest}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <h3 style={{ font: size === 'lg' ? 'var(--type-title)' : 'var(--type-heading)', letterSpacing: 'var(--ls-heading)' }}>{title}</h3>
          {meta ? <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>{meta}</span> : null}
        </div>
        {description ? <p style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)', maxWidth: '68ch', textWrap: 'pretty' }}>{description}</p> : null}
      </div>
      {actions ? <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: '0 0 auto' }}>{actions}</div> : null}
    </div>
  );
}
