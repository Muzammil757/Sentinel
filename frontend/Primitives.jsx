(() => {
const { Icon } = window.SentinelDesignSystem_8a81b0;

/* Typographic grouping: an eyebrow, a rule, and space. No card, no border box. */
function Block({ eyebrow, title, meta, actions, children, gap = 14, style }) {
  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap, minWidth: 0, ...style }}>
      {(eyebrow || title || actions) ? (
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, paddingBottom: 9, borderBottom: '1px solid var(--border-hairline)' }}>
          {eyebrow ? <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>{eyebrow}</span> : null}
          {title ? <span style={{ font: 'var(--fw-medium) var(--fs-14)/1.3 var(--font-sans)' }}>{title}</span> : null}
          {meta ? <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>{meta}</span> : null}
          <div style={{ flex: 1 }} />
          {actions}
        </div>
      ) : null}
      {children}
    </section>
  );
}

/* One operational signal: a word, a number, a state. No box. */
function Signal({ label, value, state = 'allowed', note }) {
  const dot = { allowed: 'var(--status-allowed-dot)', escalated: 'var(--status-escalated-dot)', blocked: 'var(--status-blocked-dot)', neutral: 'var(--text-tertiary)' }[state];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5, minWidth: 0 }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
        <span style={{ width: 5, height: 5, borderRadius: 99, background: dot, flex: '0 0 auto' }} />
        <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)' }}>{label}</span>
      </span>
      <span data-numeric style={{ font: 'var(--fw-medium) 19px/1 var(--font-mono)', color: 'var(--text-primary)' }}>{value}</span>
      {note ? <span style={{ font: 'var(--type-caption)', color: 'var(--text-tertiary)' }}>{note}</span> : null}
    </div>
  );
}

/* Progressive disclosure: level 3 opens in place, closed by default. */
function Disclosure({ label, count, children, defaultOpen = false }) {
  const [open, setOpen] = React.useState(defaultOpen);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: open ? 16 : 0 }}>
      <button type="button" onClick={() => setOpen(!open)}
        style={{ display: 'flex', alignItems: 'center', gap: 7, alignSelf: 'flex-start', padding: '4px 0', border: 0, background: 'none',
          cursor: 'pointer', color: 'var(--text-secondary)', font: 'var(--type-body-sm)', transition: 'var(--transition-control)' }}>
        <Icon name={open ? 'chevron-down' : 'chevron-right'} size={13} style={{ color: 'var(--text-tertiary)' }} />
        {label}
        {count != null ? <span data-numeric style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>{count}</span> : null}
      </button>
      {open ? children : null}
    </div>
  );
}

/* Outcome as a word, not a pill. */
function Outcome({ status, size = 'md' }) {
  const map = {
    allowed: ['Executed', 'var(--status-allowed-fg)'], blocked: ['Blocked', 'var(--status-blocked-fg)'],
    escalated: ['Escalated', 'var(--status-escalated-fg)'], failed: ['Failed', '#D96B6B', 'var(--fs-16)'],
    conflict: ['Conflict', 'var(--status-conflict-fg)'], pending: ['Pending', 'var(--status-pending-fg)'],
    review: ['In review', 'var(--text-secondary)'],
  };
  const entry = map[status] || map.pending;
  return <span style={{ font: `var(--fw-semibold) ${size === 'lg' ? 'var(--fs-16)' : entry[2] || 'var(--fs-15)'}/1.2 var(--font-sans)`, color: entry[1] }}>{entry[0]}</span>;
}

function Sparkline({ points = [], tone = 'neutral', height = 24 }) {
  const max = Math.max.apply(null, points.concat([1]));
  const color = tone === 'blocked' ? 'var(--status-blocked-dot)' : tone === 'escalated' ? 'var(--status-escalated-dot)' : tone === 'allowed' ? 'var(--status-allowed-dot)' : 'var(--text-tertiary)';
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height }}>
      {points.map((p, i) => <span key={i} style={{ width: 5, flex: '0 0 auto', height: Math.max(2, (p / max) * height), background: color, opacity: i === points.length - 1 ? 1 : 0.4 }} />)}
    </div>
  );
}

/* The signature chain as a quiet band of stage names. Used sparingly, never per row. */
function ChainBand({ marks = {}, note }) {
  const LINKS = ['Agents', 'Conflict', 'Resolve', 'Weigh', 'Govern', 'Executor'];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        {LINKS.map((l, i) => {
          const m = marks[l.toLowerCase()];
          const color = m === 'stop' ? '#37773E' : m === 'hold' ? 'var(--status-escalated-fg)' : m === 'split' ? 'var(--status-conflict-fg)' : 'var(--text-tertiary)';
          return (
            <React.Fragment key={l}>
              <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color, whiteSpace: 'nowrap' }}>{l}</span>
              {i < LINKS.length - 1 ? <span style={{ flex: 1, height: 1, minWidth: 12, margin: '0 10px', background: 'var(--border-subtle)' }} /> : null}
            </React.Fragment>
          );
        })}
      </div>
      {note ? <span style={{ font: 'var(--type-caption)', color: 'var(--text-tertiary)' }}>{note}</span> : null}
    </div>
  );
}

Object.assign(window, { Block, Signal, Disclosure, Outcome, Sparkline, ChainBand });
})();
