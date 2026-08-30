(() => {
const { Icon } = window.SentinelDesignSystem_8a81b0;

const SURFACES = [
  { value: 'overview', label: 'Control plane' },
  { value: 'cases', label: 'Cases' },
  { value: 'review', label: 'Human review' },
  { value: 'reliability', label: 'Reliability' },
  { value: 'audit', label: 'Audit' },
  { value: 'scenario', label: 'Scenario' },
];

function SurfaceLink({ item, active, count, onSelect }) {
  const [hover, setHover] = React.useState(false);
  return (
    <button type="button" onClick={() => onSelect(item.value)}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', gap: 6, height: 40, padding: '0 2px',
        border: 0, background: 'none', cursor: 'pointer',
        color: active ? 'var(--text-primary)' : hover ? 'var(--text-secondary)' : 'var(--text-tertiary)',
        font: 'var(--fw-medium) var(--fs-13)/1 var(--font-sans)', letterSpacing: 'var(--ls-body)', whiteSpace: 'nowrap',
        transition: 'var(--transition-control)' }}>
      {item.label}
      {count ? <span data-numeric style={{ font: 'var(--type-mono)', color: active ? 'var(--text-tertiary)' : 'inherit' }}>{count}</span> : null}
      <span style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 1, background: active ? 'var(--text-primary)' : 'transparent' }} />
    </button>
  );
}

function CommandBar({ view, onSelect, counts, attention }) {
  return (
    <header style={{ flex: '0 0 auto', borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-app)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 26, padding: '0 28px', minWidth: 940 }}>
        <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: 9, paddingRight: 8 }}>
          <span style={{ font: 'var(--fw-semibold) 14px/1 var(--font-sans)', letterSpacing: '-0.02em' }}>Sentinel</span>
          <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>production</span>
        </span>
        <nav style={{ display: 'flex', alignItems: 'center', gap: 22, minWidth: 0 }}>
          {SURFACES.map((s) => <SurfaceLink key={s.value} item={s} active={view === s.value} count={counts[s.value]} onSelect={onSelect} />)}
        </nav>
        <div style={{ flex: 1 }} />
        {attention ? (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, font: 'var(--type-body-sm)', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
            <span style={{ width: 5, height: 5, borderRadius: 99, background: 'var(--status-escalated-dot)' }} />
            {attention} need attention
          </span>
        ) : null}
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>
          <Icon name="search" size={12} />⌘K
        </span>
      </div>
    </header>
  );
}

Object.assign(window, { CommandBar, SURFACES });
})();
