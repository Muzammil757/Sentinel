(() => {
const { CausalChain, Button, IconButton, StatusBadge, InlineNotice, Icon, Badge } = window.SentinelDesignSystem_8a81b0;
const { Block } = window;

function Scenario({ steps, onOpen }) {
  const [i, setI] = React.useState(0);
  const step = steps[i];
  const last = i === steps.length - 1;
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 400px', height: '100%', minHeight: 0 }}>
      <div style={{ padding: '24px 24px 40px', display: 'flex', flexDirection: 'column', gap: 24, overflow: 'auto' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>Scenario</span>
          <h1 style={{ font: 'var(--fw-semibold) 24px/1.15 var(--font-sans)', letterSpacing: '-0.022em' }}>Walk one case through the chain</h1>
          <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)', maxWidth: '72ch' }}>A ₹18,40,000 vendor payout, replayed step by step — what each link did, and where the action stopped.</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 18, paddingTop: 8, borderTop: '1px solid var(--border-subtle)' }}>
          <CausalChain states={step.chain} detail={`t+${step.t}`} style={{ minWidth: 620 }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
              <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--accent)' }}>{step.link}</span>
              <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>step {i + 1} of {steps.length}</span>
            </span>
            <span style={{ font: 'var(--fw-semibold) 18px/1.3 var(--font-sans)', letterSpacing: 'var(--ls-heading)' }}>{step.title}</span>
            <span style={{ font: 'var(--type-body)', color: 'var(--text-secondary)', maxWidth: '70ch', textWrap: 'pretty' }}>{step.body}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Button icon="chevron-left" disabled={i === 0} onClick={() => setI(Math.max(0, i - 1))}>Back</Button>
            {last ? (
              <Button variant="primary" trailingIcon="arrow-up-right" onClick={() => onOpen('CASE-2041')}>Open the decision record</Button>
            ) : (
              <Button variant="primary" onClick={() => setI(i + 1)}>Next &gt;</Button>
            )}
            <div style={{ flex: 1 }} />
            <Button variant="ghost" icon="rotate-ccw" onClick={() => setI(0)}>Restart</Button>
          </div>
        </div>

        {last ? (
          <InlineNotice tone="blocked" title="Nothing executed">
            The executor was never called. This is the product's whole point: the chain stops at GOVERN, the reasons are recorded, and a human annotates rather than overrides.
          </InlineNotice>
        ) : null}
      </div>

      <aside style={{ borderLeft: '1px solid var(--border-subtle)', background: 'var(--bg-surface)', padding: '20px', overflow: 'auto' }}>
        <Block eyebrow="Timeline" title="Chain replay">
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {steps.map((s, idx) => {
              const active = idx === i;
              const done = idx < i;
              return (
                <button key={s.link + idx} type="button" onClick={() => setI(idx)}
                  style={{ display: 'grid', gridTemplateColumns: '54px 12px minmax(0,1fr)', gap: 10, alignItems: 'start', textAlign: 'left',
                    padding: '11px 8px', border: 0, borderBottom: '1px solid var(--border-hairline)', cursor: 'pointer',
                    background: active ? 'var(--bg-selected)' : 'transparent', transition: 'var(--transition-control)' }}>
                  <span data-numeric style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>{s.t}</span>
                  <span style={{ display: 'flex', justifyContent: 'center', paddingTop: 4 }}>
                    <span style={{ width: 6, height: 6, borderRadius: 99, background: active ? 'var(--accent)' : done ? 'var(--status-allowed-dot)' : 'transparent', border: active || done ? 'none' : '1px solid var(--border-strong)', boxShadow: active ? 'var(--glow-accent)' : 'none' }} />
                  </span>
                  <span style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
                    <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: active ? 'var(--text-primary)' : 'var(--text-tertiary)' }}>{s.link}</span>
                    <span style={{ font: 'var(--fw-regular) var(--fs-13)/1.35 var(--font-sans)', color: active ? 'var(--text-primary)' : 'var(--text-secondary)' }}>{s.title}</span>
                  </span>
                </button>
              );
            })}
          </div>
        </Block>
      </aside>
    </div>
  );
}

Object.assign(window, { Scenario });
})();
