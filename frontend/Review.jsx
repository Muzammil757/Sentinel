(() => {
const { Button, Textarea, Checkbox, Icon } = window.SentinelDesignSystem_8a81b0;
const { Outcome, Disclosure } = window;

// The original export keyed WHY/ASK by literal fixture case ids
// (CASE-2041 etc.) with hand-written narrative text -- real case ids would
// just render undefined. WHY is replaced by each case's real
// `shortReason` (Data.jsx: the real conflict reason, or GOVERN's real
// outcome sentence when there's no conflict). ASK -- a fixture-only
// "what to confirm" narrative with no backend equivalent -- is replaced
// below with GOVERN's own real `reasons` list rather than invented
// questions.

function Review({ cases, onOpen, onToast }) {
  const queue = cases.filter((c) => c.stages.some((s) => s.label === 'Review' && s.state === 'active'));
  const [sel, setSel] = React.useState(queue[0] ? queue[0].id : null);
  const [note, setNote] = React.useState('');
  const [flagPolicy, setFlagPolicy] = React.useState(false);
  const c = queue.find((q) => q.id === sel) || queue[0];

  // The original export always had at least one fixture case waiting for
  // review; a real, healthy Sentinel can genuinely have zero.
  if (!c) {
    return (
      <div style={{ overflow: 'auto', height: '100%' }}>
        <div style={{ maxWidth: 1000, margin: '0 auto', padding: '44px 28px 80px', display: 'flex', flexDirection: 'column', gap: 10 }}>
          <h1 style={{ font: 'var(--fw-semibold) 22px/1.2 var(--font-sans)', letterSpacing: '-0.022em' }}>Human review</h1>
          <p style={{ font: 'var(--type-body)', color: 'var(--text-secondary)' }}>No cases are waiting for review.</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ overflow: 'auto', height: '100%' }}>
      <div style={{ maxWidth: 1000, margin: '0 auto', padding: '44px 28px 80px', display: 'flex', flexDirection: 'column', gap: 34 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <h1 style={{ font: 'var(--fw-semibold) 22px/1.2 var(--font-sans)', letterSpacing: '-0.022em' }}>Human review</h1>
          <p style={{ font: 'var(--type-body)', color: 'var(--text-secondary)', maxWidth: '62ch' }}>
            {queue.length} cases are waiting for context from a person. Sentinel has already decided each one — review records what a decision could not know.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 24, borderBottom: '1px solid var(--border-hairline)' }}>
          {queue.map((q) => {
            const active = c && q.id === c.id;
            return (
              <button key={q.id} type="button" onClick={() => setSel(q.id)}
                style={{ position: 'relative', display: 'inline-flex', alignItems: 'baseline', gap: 8, height: 34, border: 0, background: 'none', padding: 0, cursor: 'pointer',
                  color: active ? 'var(--text-primary)' : 'var(--text-tertiary)', font: 'var(--type-mono)', transition: 'var(--transition-control)' }}>
                {q.id}
                <span style={{ font: 'var(--fw-regular) var(--fs-12)/1 var(--font-sans)' }}>{q.notes.length} note{q.notes.length === 1 ? '' : 's'}</span>
                <span style={{ position: 'absolute', left: 0, right: 0, bottom: -1, height: 1, background: active ? 'var(--text-primary)' : 'transparent' }} />
              </button>
            );
          })}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>{c.domain} · {c.value}</span>
            <Outcome status={c.status} />
          </span>
          <h2 style={{ font: 'var(--fw-semibold) 22px/1.25 var(--font-sans)', letterSpacing: '-0.02em', maxWidth: '30ch' }}>{c.title}</h2>
          <p style={{ font: 'var(--fw-regular) var(--fs-16)/1.5 var(--font-sans)', color: 'var(--text-secondary)', maxWidth: '64ch', textWrap: 'pretty' }}>{c.shortReason}</p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)', gap: 40 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>Sentinel already decided</span>
            <span style={{ font: 'var(--type-body)', textWrap: 'pretty' }}>{c.headline}</span>
            <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>policy {c.policy} · decided by GOVERN</span>
            <button type="button" onClick={() => onOpen(c.id)} style={{ alignSelf: 'flex-start', border: 0, background: 'none', padding: 0, cursor: 'pointer', color: 'var(--text-secondary)', font: 'var(--type-body-sm)' }}>See the reasoning →</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>What GOVERN considered</span>
            {c.reasons.map((r, i) => (
              <span key={i} style={{ display: 'flex', gap: 9, font: 'var(--type-body)', textWrap: 'pretty' }}>
                <span style={{ color: 'var(--text-tertiary)' }}>{i + 1}</span>{r.value}
              </span>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14, paddingTop: 22, borderTop: '1px solid var(--border-subtle)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 8, font: 'var(--type-body-sm)', color: 'var(--text-secondary)' }}>
            <Icon name="lock" size={13} style={{ color: 'var(--text-tertiary)' }} />
            Review annotates. It cannot allow, block, override or retry — GOVERN keeps that authority.
          </span>
          <Textarea rows={5} value={note} onChange={(e) => setNote(e.target.value)} placeholder="What should a future reviewer or policy owner know?" counter={`${note.length}/500`} />
          <Checkbox
            label="Flag the governing policy for owner review"
            description={`policy ${c.policy} · routed to the policy owner, not the executor`}
            checked={flagPolicy}
            onChange={(e) => setFlagPolicy(e.target.checked)}
          />
          <div style={{ display: 'flex', gap: 10 }}>
            <Button variant="primary" onClick={() => { setNote(''); setFlagPolicy(false); onToast(); }}>Record note</Button>
            <Button variant="ghost" onClick={() => { setNote(''); setFlagPolicy(false); }}>Discard</Button>
          </div>
          {c.notes.length ? (
            <Disclosure label="Earlier notes" count={c.notes.length}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {c.notes.map((n, i) => (
                  <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 3, maxWidth: '68ch' }}>
                    <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>{n.who} · {n.when}</span>
                    <span style={{ font: 'var(--type-body-sm)', textWrap: 'pretty' }}>{n.text}</span>
                  </div>
                ))}
              </div>
            </Disclosure>
          ) : null}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Review });
})();
