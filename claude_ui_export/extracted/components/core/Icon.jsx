import React from 'react';

const CDN = 'https://unpkg.com/lucide-static@0.469.0/icons/';

/* Lucide (1.5px stroke) is the substituted icon set for Sentinel — glyphs are loaded as
   CSS masks so they inherit currentColor and stay crisp at 14–20px. */
export function Icon({ name, size = 16, strokeAlign = 'center', style, className, ...rest }) {
  return (
    <span
      role="img"
      aria-hidden="true"
      data-icon={name}
      className={className}
      style={{
        display: 'inline-block',
        width: size,
        height: size,
        flex: '0 0 auto',
        backgroundColor: 'currentColor',
        WebkitMask: `url(${CDN}${name}.svg) ${strokeAlign} / contain no-repeat`,
        mask: `url(${CDN}${name}.svg) ${strokeAlign} / contain no-repeat`,
        ...style,
      }}
      {...rest}
    />
  );
}
