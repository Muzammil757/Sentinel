(() => {
const { Input } = window.SentinelDesignSystem_8a81b0;
const { Outcome } = window;

const QUEUES = [
  { value: 'attention', label: 'Needs attention' },
  { value: 'all', label: 'All' },
  { value: 'allowed', label: 'Executed' },
];

function Row({ c, onOpen, last }) {
  const [hover, setHover] = React.useState(false);
  return (
    <div onClick={() => onOpen(c.id)} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{ display: 'grid', gridTemplateColumns: '108px minmax(0,1.6fr) 180px minmax(0,1fr) 92px', gap: 20, alignItems: 'baseline',
        padding: '15px 8px 15px 0', minWidth: 720, cursor: 'pointer',
        borderBottom: last ? 0 : '1px solid var(--border-hairline)',
        background: hover ? 'var(--bg-hover)' : 'transparent', transition: 'var(--transition-control)' }}>
      <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>{c.id}</span>
      <span style={{ font: 'var(--fw-medium) var(--fs-14)/1.3 var(--font-sans)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.title}</span>
      <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-tertiary)' }}>{c.domain} · {c.value}</span>
      <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.shortReason}</span>
      <span style={{ display: 'flex', justifyContent: 'flex-end' }}><Outcome status={c.status} /></span>
    </div>
  );
}

function Cases({ cases, onOpen }) {
  const [queue, setQueue] = React.useState('attention');
  const list = cases.filter((c) => queue === 'all' ? true : queue === 'attention' ? ['blocked', 'escalated', 'failed'].includes(c.status) : c.status === 'allowed');
  const n = (v) => v === 'all' ? cases.length : v === 'attention' ? cases.filter((c) => ['blocked','escalated','failed'].includes(c.status)).length : cases.filter((c) => c.status === 'allowed').length;
  return (
    <div style={{ overflow: 'auto', height: '100%' }}>
      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '44px 28px 72px', display: 'flex', flexDirection: 'column', gap: 26 }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 24, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <h1 style={{ font: 'var(--fw-semibold) 22px/1.2 var(--font-sans)', letterSpacing: '-0.022em' }}>Cases</h1>
            <p style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)' }}>Automated actions Sentinel decided on. Open one to see why.</p>
          </div>
          <div style={{ flex: 1 }} />
          <Input icon="search" placeholder="Case, surface or policy" mono wrapperStyle={{ width: 220 }} />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 22, borderBottom: '1px solid var(--border-hairline)' }}>
          {QUEUES.map((q) => {
            const active = queue === q.value;
            return (
              <button key={q.value} type="button" onClick={() => setQueue(q.value)}
                style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', gap: 6, height: 32, padding: 0, border: 0, background: 'none', cursor: 'pointer',
                  color: active ? 'var(--text-primary)' : 'var(--text-tertiary)', font: 'var(--fw-medium) var(--fs-13)/1 var(--font-sans)', transition: 'var(--transition-control)' }}>
                {q.label}<span data-numeric style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>{n(q.value)}</span>
                <span style={{ position: 'absolute', left: 0, right: 0, bottom: -1, height: 1, background: active ? 'var(--text-primary)' : 'transparent' }} />
              </button>
            );
          })}
        </div>

        <div>{list.map((c, i) => <Row key={c.id} c={c} onOpen={onOpen} last={i === list.length - 1} />)}</div>
        <span style={{ font: 'var(--type-caption)', color: 'var(--text-tertiary)' }}>Reasoning, candidates, execution and audit detail live inside each case.</span>
      </div>
    </div>
  );
}

Object.assign(window, { Cases });
})();
