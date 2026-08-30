(() => {
const { Block, Signal, ChainBand, Outcome } = window;

function AttentionItem({ c, onOpen, last }) {
  const [hover, setHover] = React.useState(false);
  return (
    <div onClick={() => onOpen(c.id)} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{ display: 'grid', gridTemplateColumns: '108px minmax(0,1fr) 200px 96px', gap: 20, alignItems: 'baseline',
        padding: '16px 8px 16px 0', cursor: 'pointer', borderBottom: last ? 0 : '1px solid var(--border-hairline)',
        background: hover ? 'var(--bg-hover)' : 'transparent', transition: 'var(--transition-control)' }}>
      <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>{c.id}</span>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5, minWidth: 0 }}>
        <span style={{ font: 'var(--fw-medium) var(--fs-15)/1.3 var(--font-sans)', letterSpacing: '-0.008em' }}>{c.title}</span>
        <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)', textWrap: 'pretty' }}>{c.shortReason}</span>
      </div>
      <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-tertiary)' }}>{c.domain} · {c.value}</span>
      <span style={{ display: 'flex', justifyContent: 'flex-end' }}><Outcome status={c.status} /></span>
    </div>
  );
}

function Overview({ cases, onOpen, onGo }) {
  const attention = cases.filter((c) => ['blocked', 'escalated', 'failed'].includes(c.status));
  return (
    <div style={{ overflow: 'auto', height: '100%' }}>
      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '56px 28px 72px', display: 'flex', flexDirection: 'column', gap: 54 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>Last 24 hours</span>
          <h1 style={{ font: 'var(--fw-semibold) 30px/1.2 var(--font-sans)', letterSpacing: '-0.026em', maxWidth: '24ch' }}>
            Sentinel governed 412 automated actions. Three stopped.
          </h1>
          <p style={{ font: 'var(--type-body)', color: 'var(--text-secondary)', maxWidth: '62ch', textWrap: 'pretty' }}>
            396 executed as decided. Twelve were blocked by policy, four escalated for review, two failed downstream. Nothing executed without a GOVERN decision.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0,1fr))', gap: 32 }}>
          <Signal label="Execution" value="99.4%" note="396 of 398 calls succeeded" state="allowed" />
          <Signal label="Governance latency" value="118ms" note="p99, budget 150ms" state="escalated" />
          <Signal label="Agent conflict" value="9.2%" note="38 cases needed RESOLVE" state="escalated" />
          <Signal label="Audit completeness" value="100%" note="no gaps in 30 days" state="allowed" />
        </div>

        <Block eyebrow="Needs attention" title={attention.length + ' cases the system could not close'}
          actions={<button type="button" onClick={() => onGo('cases')} style={{ border: 0, background: 'none', cursor: 'pointer', color: 'var(--text-secondary)', font: 'var(--type-body-sm)' }}>All cases →</button>}>
          <div>{attention.map((c, i) => <AttentionItem key={c.id} c={c} onOpen={onOpen} last={i === attention.length - 1} />)}</div>
        </Block>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <ChainBand marks={{ conflict: 'split', govern: 'stop' }}
            note="Every action crosses these six stages. Today 38 split at CONFLICT and 16 stopped at GOVERN." />
          <button type="button" onClick={() => onGo('scenario')}
            style={{ alignSelf: 'flex-start', border: 0, background: 'none', padding: 0, cursor: 'pointer', color: 'var(--text-secondary)', font: 'var(--type-body-sm)' }}>
            Walk a case through the chain →
          </button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Overview });
})();
