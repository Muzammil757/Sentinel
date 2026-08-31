(() => {
const { Block, Signal, ChainBand, Outcome } = window;

/*
 * Real-data edits only -- layout, spacing, typography and the Block/Signal/
 * ChainBand/Outcome components are byte-identical to the design export.
 * The original hardcoded headline ("Sentinel governed 412 automated
 * actions...", fixed 99.4%/118ms/9.2%/100% signals, "38 split at CONFLICT
 * and 16 stopped at GOVERN") is replaced with values computed from the
 * `cases` prop -- the same real, already-wired array Cases.jsx and
 * DecisionRecord.jsx use. Nothing here is fetched separately or fabricated.
 *
 * Of the four original signals, three are genuinely derivable from fields
 * already on each mapped case (see frontend/Data.jsx): execution success
 * from `exec`, agent conflict rate from `conflict`, audit completeness from
 * `audit`. "Governance latency" has no real equivalent anywhere in this
 * backend -- no per-stage GOVERN timing is recorded, and policy_bundle.yaml
 * defines no latency budget at all -- so that card is omitted rather than
 * shown with an invented number.
 */

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
  const total = cases.length;

  // Execution success: real receipts already on each case (Data.jsx's `exec`,
  // present only for cases that reached EXECUTOR).
  const withExec = cases.filter((c) => c.exec);
  const execSucceeded = withExec.filter((c) => c.exec.result && !c.exec.result.startsWith('Failed')).length;
  const execSignal = withExec.length
    ? { label: 'Execution', value: `${((execSucceeded / withExec.length) * 100).toFixed(1)}%`, note: `${execSucceeded} of ${withExec.length} calls succeeded`, state: execSucceeded === withExec.length ? 'allowed' : 'escalated' }
    : null;

  // Agent conflict rate: real `conflict` boolean on every case.
  const conflictCount = cases.filter((c) => c.conflict).length;
  const conflictSignal = total
    ? { label: 'Agent conflict', value: `${((conflictCount / total) * 100).toFixed(1)}%`, note: `${conflictCount} of ${total} cases needed RESOLVE`, state: conflictCount ? 'escalated' : 'allowed' }
    : null;

  // Audit completeness: every case's own real `audit` array, already loaded.
  const withAudit = cases.filter((c) => c.audit && c.audit.length > 0).length;
  const auditSignal = total
    ? { label: 'Audit completeness', value: `${((withAudit / total) * 100).toFixed(1)}%`, note: `${withAudit} of ${total} runs have a recorded trail`, state: withAudit === total ? 'allowed' : 'escalated' }
    : null;

  // "Governance latency" is deliberately absent -- see file header. No
  // fourth signal is substituted in its place.
  const signals = [execSignal, conflictSignal, auditSignal].filter(Boolean);

  const govHalted = cases.filter((c) => c.status === 'escalated').length;
  const failedCount = cases.filter((c) => c.status === 'failed').length;
  const chainMarks = {};
  if (conflictCount) chainMarks.conflict = 'split';
  if (govHalted) chainMarks.govern = 'stop';
  const chainNote = total
    ? `Every action crosses these six stages. ${conflictCount} split at CONFLICT and ${govHalted} stopped at GOVERN, of ${total} case${total === 1 ? '' : 's'} total.`
    : 'No cases recorded yet.';

  return (
    <div style={{ overflow: 'auto', height: '100%' }}>
      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '56px 28px 72px', display: 'flex', flexDirection: 'column', gap: 54 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>All cases</span>
          <h1 style={{ font: 'var(--fw-semibold) 30px/1.2 var(--font-sans)', letterSpacing: '-0.026em', maxWidth: '28ch' }}>
            Sentinel governed {total} automated action{total === 1 ? '' : 's'}. {attention.length} stopped.
          </h1>
          <p style={{ font: 'var(--type-body)', color: 'var(--text-secondary)', maxWidth: '62ch', textWrap: 'pretty' }}>
            {execSucceeded} executed as decided. {govHalted} {govHalted === 1 ? 'was' : 'were'} escalated for review, {failedCount} failed or {failedCount === 1 ? 'was' : 'were'} rejected downstream. Nothing executed without a GOVERN decision.
          </p>
        </div>

        {signals.length ? (
          <div style={{ display: 'grid', gridTemplateColumns: `repeat(${signals.length}, minmax(0,1fr))`, gap: 32 }}>
            {signals.map((s) => <Signal key={s.label} {...s} />)}
          </div>
        ) : null}

        <Block eyebrow="Needs attention" title={attention.length + ' cases the system could not close'}
          actions={<button type="button" onClick={() => onGo('cases')} style={{ border: 0, background: 'none', cursor: 'pointer', color: 'var(--text-secondary)', font: 'var(--type-body-sm)' }}>All cases →</button>}>
          {attention.length ? (
            <div>{attention.map((c, i) => <AttentionItem key={c.id} c={c} onOpen={onOpen} last={i === attention.length - 1} />)}</div>
          ) : (
            <p style={{ font: 'var(--type-body-sm)', color: 'var(--text-tertiary)' }}>All cases are clear.</p>
          )}
        </Block>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <ChainBand marks={chainMarks} note={chainNote} />
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Overview });
})();
