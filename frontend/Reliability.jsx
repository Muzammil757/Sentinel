(() => {
const { Icon } = window.SentinelDesignSystem_8a81b0;
const { Signal, Sparkline, Block } = window;

const LATENCY = [62,71,68,79,74,88,84,96,91,104,99,112,108,118,116];

function Reliability({ executors, cases }) {
  const failed = cases.filter((c) => c.status === 'failed');
  return (
    <div style={{ overflow: 'auto', height: '100%' }}>
      <div style={{ maxWidth: 1000, margin: '0 auto', padding: '44px 28px 80px', display: 'flex', flexDirection: 'column', gap: 46 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <h1 style={{ font: 'var(--fw-semibold) 22px/1.2 var(--font-sans)', letterSpacing: '-0.022em' }}>Reliability</h1>
          <p style={{ font: 'var(--type-body)', color: 'var(--text-secondary)', maxWidth: '62ch', textWrap: 'pretty' }}>
            The control plane is trustworthy right now. Governance latency is inside budget but climbing, and both execution failures today came from one region.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0,1fr))', gap: 32 }}>
          <Signal label="Execution success" value="99.4%" note="2 failures in 398 calls" state="allowed" />
          <Signal label="Governance latency" value="118ms" note="p99 of a 150ms budget" state="escalated" />
          <Signal label="Agent agreement" value="90.8%" note="38 conflicts resolved" state="allowed" />
          <Signal label="Audit completeness" value="100%" note="verified hourly, 30d" state="allowed" />
        </div>

        <Block eyebrow="Governance latency" title="p99 over the last 3 hours" meta="budget 150ms">
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 16 }}>
            <Sparkline points={LATENCY} tone="escalated" height={56} />
            <span data-numeric style={{ font: 'var(--fw-medium) 17px/1 var(--font-mono)', color: 'var(--status-escalated-fg)' }}>118ms</span>
          </div>
          <span style={{ font: 'var(--type-caption)', color: 'var(--text-tertiary)' }}>Rising with conflict volume — RESOLVE runs on every disagreement.</span>
        </Block>

        <Block eyebrow="Workers" title="Execution capacity">
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {executors.map((e, i) => (
              <div key={e.region} style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 90px 90px 140px', gap: 20, alignItems: 'baseline', padding: '13px 0', borderBottom: i === executors.length - 1 ? 0 : '1px solid var(--border-hairline)' }}>
                <span style={{ font: 'var(--type-mono)' }}>{e.region}</span>
                <span data-numeric style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>queue {e.depth}</span>
                <span data-numeric style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>{e.last}</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 7, font: 'var(--type-body-sm)', color: e.state === 'allowed' ? 'var(--text-secondary)' : 'var(--status-escalated-fg)' }}>
                  <span style={{ width: 5, height: 5, borderRadius: 99, background: e.state === 'allowed' ? 'var(--status-allowed-dot)' : 'var(--status-escalated-dot)' }} />{e.note}
                </span>
              </div>
            ))}
          </div>
          <span style={{ font: 'var(--type-caption)', color: 'var(--text-tertiary)' }}>Queue depth above 5 raises an escalation, never a block.</span>
        </Block>

        <Block eyebrow="Failures" title="Execution failures today" meta={String(failed.length)}>
          {failed.map((c) => (
            <div key={c.id} style={{ display: 'grid', gridTemplateColumns: '108px minmax(0,1fr) 200px', gap: 20, alignItems: 'baseline', padding: '4px 0' }}>
              <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>{c.id}</span>
              <span style={{ font: 'var(--type-body-sm)', textWrap: 'pretty' }}>{c.title} — {c.reasons[1].value}</span>
              <span style={{ font: 'var(--type-body-sm)', color: 'var(--status-blocked-fg)' }}>us-east-1 · HTTP 503</span>
            </div>
          ))}
          <span style={{ font: 'var(--type-caption)', color: 'var(--text-tertiary)' }}>A failed execution never retries without a fresh GOVERN decision.</span>
        </Block>
      </div>
    </div>
  );
}

Object.assign(window, { Reliability });
})();
