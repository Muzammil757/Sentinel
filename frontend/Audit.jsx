(() => {
const { Input, Button } = window.SentinelDesignSystem_8a81b0;

const STAGES = ['all', 'intake', 'agents', 'conflict', 'govern', 'executor', 'reviewer', 'system'];
const STAGE_COLOR = { govern: 'var(--text-primary)', conflict: 'var(--status-conflict-fg)', executor: 'var(--teal)', reviewer: 'var(--status-escalated-fg)' };

function Audit({ audit }) {
  const [stage, setStage] = React.useState('all');
  const entries = stage === 'all' ? audit : audit.filter((e) => String(e.actor) === stage);
  return (
    <div style={{ overflow: 'auto', height: '100%' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto', padding: '44px 28px 80px', display: 'flex', flexDirection: 'column', gap: 24 }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 24, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <h1 style={{ font: 'var(--fw-semibold) 22px/1.2 var(--font-sans)', letterSpacing: '-0.022em' }}>Audit</h1>
            <p style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)' }}>Append-only. 18,402 entries over 30 days · retention 7 years.</p>
          </div>
          <div style={{ flex: 1 }} />
          <Input icon="search" mono placeholder="case, policy or reference" wrapperStyle={{ width: 230 }} />
          <Button size="md" variant="ghost" icon="download">Export</Button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 18, borderBottom: '1px solid var(--border-hairline)', flexWrap: 'wrap' }}>
          {STAGES.map((s) => {
            const active = stage === s;
            return (
              <button key={s} type="button" onClick={() => setStage(s)}
                style={{ position: 'relative', height: 30, border: 0, background: 'none', padding: 0, cursor: 'pointer',
                  color: active ? 'var(--text-primary)' : 'var(--text-tertiary)', font: 'var(--type-mono)', transition: 'var(--transition-control)' }}>
                {s}
                <span style={{ position: 'absolute', left: 0, right: 0, bottom: -1, height: 1, background: active ? 'var(--text-primary)' : 'transparent' }} />
              </button>
            );
          })}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {entries.map((e, i) => (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '132px 96px minmax(0,1fr) 220px', gap: 20, alignItems: 'baseline',
              padding: '9px 0', borderBottom: i === entries.length - 1 ? 0 : '1px solid var(--border-hairline)', minWidth: 700 }}>
              <span data-numeric style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>{e.time}</span>
              <span style={{ font: 'var(--type-mono)', color: STAGE_COLOR[e.actor] || 'var(--text-secondary)' }}>{e.actor}</span>
              <span style={{ font: 'var(--type-body-sm)', textWrap: 'pretty' }}>{e.message}</span>
              <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.detail || '—'}</span>
            </div>
          ))}
        </div>
        <span style={{ font: 'var(--type-caption)', color: 'var(--text-tertiary)' }}>Showing {entries.length} of 18,402 entries. Entries cannot be edited or removed, including reviewer annotations.</span>
      </div>
    </div>
  );
}

Object.assign(window, { Audit });
})();
