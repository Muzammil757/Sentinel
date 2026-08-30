(() => {
const { Button, Textarea, Dialog, AuditTrail, Icon } = window.SentinelDesignSystem_8a81b0;
const { Disclosure } = window;

/* One state table drives the whole record, so all four outcomes stay honest and consistent. */
const STATE = {
  blocked: {
    verdict: 'Blocked', tone: 'var(--status-blocked-fg)', authority: 'Denied',
    govern: 'GOVERN denied execution.',
    execLead: 'Not reached', execTone: '#D2664E',
  },
  escalated: {
    verdict: 'Escalated', tone: 'var(--status-escalated-fg)', authority: 'Withheld',
    govern: 'GOVERN did not authorise autonomous execution and routed the case for human review.',
    execLead: 'Not executed', execTone: 'var(--status-escalated-fg)',
  },
  failed: {
    verdict: 'Failed', tone: '#D96B6B', authority: 'Granted', decision: 'Allowed',
    govern: 'GOVERN allowed the action; the failure happened downstream.',
    execLead: 'Execution failed', execTone: '#D96B6B',
  },
  allowed: {
    verdict: 'Executed', tone: 'var(--status-allowed-fg)', authority: 'Granted', decision: 'Allowed',
    govern: 'GOVERN authorised the action.',
    execLead: 'Executed successfully', execTone: 'var(--status-allowed-fg)',
  },
};

const MARK = { stop: 'var(--status-blocked-fg)', hold: 'var(--status-escalated-fg)', split: 'var(--status-conflict-fg)', none: 'var(--border-emphasis)' };

/* Compact supporting stage: label, one line, optional evidence. Never competes with the verdict. */
function Stage({ label, mark = 'none', summary, children, last = false }) {
  const filled = mark !== 'none';
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '92px 11px minmax(0,1fr)', columnGap: 20, alignItems: 'stretch' }}>
      <div style={{ paddingTop: 2, textAlign: 'right' }}>
        <span style={{ font: 'var(--type-label)', fontSize: filled ? 'var(--fs-16)' : 'var(--fs-15)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: filled ? MARK[mark] : 'var(--text-secondary)' }}>{label}</span>
      </div>
      <div style={{ position: 'relative', display: 'flex', justifyContent: 'center' }}>
        <span style={{ width: 1, background: last ? 'transparent' : 'var(--border-subtle)' }} />
        <span style={{ position: 'absolute', top: 5, width: 5, height: 5, borderRadius: 99, background: filled ? MARK[mark] : 'var(--border-emphasis)', boxShadow: '0 0 0 4px var(--bg-app)' }} />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 7, paddingBottom: last ? 0 : 18, minWidth: 0 }}>
        {summary ? <span style={{ font: 'var(--fw-regular) var(--fs-14)/1.45 var(--font-sans)', color: 'var(--text-secondary)', maxWidth: '62ch', textWrap: 'pretty' }}>{summary}</span> : null}
        {children}
      </div>
    </div>
  );
}

function Positions({ positions }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0,1fr))', gap: 24 }}>
      {positions.map((p, i) => (
        <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0, paddingTop: 8, borderTop: '1px solid var(--border-hairline)' }}>
          <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>{p.agent}</span>
          <span style={{ font: 'var(--fw-medium) var(--fs-14)/1.3 var(--font-sans)', color: 'var(--text-primary)' }}>{p.position}</span>
          <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)', textWrap: 'pretty' }}>{p.basis}</span>
          <span data-numeric style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>confidence {p.confidence}</span>
        </div>
      ))}
    </div>
  );
}

function Scoring({ candidates }) {
  const top = Math.max.apply(null, candidates.map((o) => parseFloat(o.score)));
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {candidates.map((o) => {
        const chosen = o.verdict === 'chosen';
        return (
          <div key={o.rank} style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 88px 42px 72px', gap: 14, alignItems: 'center', padding: '8px 0', borderTop: '1px solid var(--border-hairline)' }}>
            <span style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0 }}>
              <span style={{ font: `${chosen ? 'var(--fw-medium)' : 'var(--fw-regular)'} var(--fs-13)/1.35 var(--font-sans)`, color: chosen ? 'var(--text-primary)' : 'var(--text-secondary)' }}>{o.name}</span>
              <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>{o.proposedBy}</span>
            </span>
            <span style={{ display: 'flex', alignItems: 'center', height: 2, background: 'var(--border-hairline)' }}>
              <span style={{ width: `${(parseFloat(o.score) / top) * 100}%`, height: 2, background: chosen ? 'var(--status-allowed-dot)' : 'var(--text-tertiary)', opacity: chosen ? 1 : .45 }} />
            </span>
            <span data-numeric style={{ font: 'var(--type-mono)', fontSize: 'var(--fs-13)', color: chosen ? 'var(--text-primary)' : 'var(--text-tertiary)', textAlign: 'right' }}>{o.score}</span>
            <span style={{ font: 'var(--type-body-sm)', textAlign: 'right', color: chosen ? 'var(--status-allowed-fg)' : o.verdict === 'rejected' ? 'var(--status-blocked-fg)' : 'var(--text-tertiary)' }}>
              {chosen ? 'Chosen' : o.verdict === 'rejected' ? 'Rejected' : 'Considered'}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/* THE VERDICT — the page's dominant element. Status word, consequence, authority facts. */
function Verdict({ c, s }) {
  const consequence = (c.status === 'blocked' || c.status === 'escalated')
    ? c.reasons[0].value
    : c.status === 'failed'
      ? (c.reasons.find((r) => r.label === 'Failure') || c.reasons[0]).value
      : (c.reasons.find((r) => r.label === 'Basis') || c.reasons[0]).value;
  return (
    <section style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 232px', gap: 40, alignItems: 'start', padding: '28px 0 30px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 0 }}>
        <span style={{ font: 'var(--fw-semibold) 46px/1 var(--font-sans)', letterSpacing: '-0.038em', color: s.tone }}>{s.verdict}</span>
        <span style={{ font: 'var(--fw-regular) 17px/1.45 var(--font-sans)', color: 'var(--text-primary)', maxWidth: '52ch', textWrap: 'pretty' }}>{consequence}</span>
        <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)', maxWidth: '56ch', textWrap: 'pretty' }}>{s.govern}</span>
      </div>
      <dl style={{ margin: 0, display: 'grid', gridTemplateColumns: 'minmax(0,1fr)', rowGap: 12, paddingLeft: 22, borderLeft: `2px solid ${s.tone}` }}>
        {[['Policy', c.policy, true], ['Decision', s.decision || s.verdict, false], ['Authority', s.authority, false]].map(([k, v, mono]) => (
          <div key={k} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <dt style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>{k}</dt>
            <dd style={{ margin: 0, font: mono ? 'var(--type-mono)' : 'var(--type-body-sm)', fontSize: 'var(--fs-13)', color: k === 'Authority' ? s.tone : 'var(--text-primary)' }}>{v}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function ExecutorBlock({ c, s }) {
  const detail = !c.exec
    ? (c.status === 'blocked'
        ? `No external call was made because GOVERN denied execution. Nothing reached ${c.surface}.`
        : 'Execution is withheld while the case is in review. The executor runs only if GOVERN allows it after a fresh evaluation.')
    : c.exec.result.startsWith('Failed')
      ? `${c.exec.target} returned ${c.exec.result.replace('Failed · ', '')} after GOVERN authorised the call. No partial state was written, and there is no automatic retry.`
      : `External action completed after GOVERN authorisation. ${c.exec.result}.`;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <span style={{ font: 'var(--fw-medium) var(--fs-16)/1.3 var(--font-sans)', color: s.execTone }}>{s.execLead}</span>
        <span style={{ font: 'var(--type-body)', color: 'var(--text-secondary)', maxWidth: '58ch', textWrap: 'pretty' }}>{detail}</span>
      </div>
      {c.exec ? (
        <Disclosure label="Show execution detail">
          <dl style={{ margin: 0, display: 'grid', gridTemplateColumns: '86px minmax(0,1fr)', rowGap: 6, columnGap: 20, maxWidth: 420, paddingTop: 8, borderTop: '1px solid var(--border-hairline)' }}>
            {[['Reference', c.exec.id], ['Target', c.exec.target], ['Duration', c.exec.duration], ['At', c.exec.at]].map(([k, v]) => (
              <React.Fragment key={k}>
                <dt style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)' }}>{k}</dt>
                <dd data-numeric style={{ margin: 0, font: 'var(--type-mono)', fontSize: 'var(--fs-13)', color: 'var(--text-primary)' }}>{v}</dd>
              </React.Fragment>
            ))}
          </dl>
        </Disclosure>
      ) : null}
    </div>
  );
}

const REVIEW_REASON = {
  'CASE-2041': 'Policy blocked a payout that finance may have re-authorised out of band. A reviewer records whether the ceiling is current.',
  'CASE-2043': 'Two agents disagreed on a name match and GOVERN withheld authority rather than guess. A reviewer records what the documents show.',
  'CASE-2044': 'GOVERN authorised the action and the partner failed mid-replay. A reviewer records whether the partner incident is closed.',
};
const REVIEW_ASK = {
  'CASE-2041': 'Whether the vendor ceiling in policy payout-v4 is current, and whether this payout was authorised elsewhere.',
  'CASE-2043': 'Whether the submitted documents resolve the name mismatch.',
  'CASE-2044': 'Whether the partner has confirmed recovery.',
};

function ReviewSection({ c, onAnnotate, onToast }) {
  return (
    <section style={{ marginTop: 32, padding: '18px 0 0 24px', borderTop: '1px solid var(--border-subtle)', borderLeft: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: 14 }}>
      <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--status-escalated-fg)' }}>Human review</span>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0,1fr))', gap: 28 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
          <span style={{ font: 'var(--fw-medium) var(--fs-14)/1.35 var(--font-sans)' }}>Why a human is here</span>
          <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)', textWrap: 'pretty' }}>{REVIEW_REASON[c.id]}</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
          <span style={{ font: 'var(--fw-medium) var(--fs-14)/1.35 var(--font-sans)' }}>What the reviewer provides</span>
          <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)', textWrap: 'pretty' }}>{REVIEW_ASK[c.id]}</span>
        </div>
      </div>
      <span style={{ display: 'flex', gap: 8, alignItems: 'flex-start', font: 'var(--type-body-sm)', color: 'var(--text-secondary)', maxWidth: '64ch', textWrap: 'pretty' }}>
        <Icon name="lock" size={13} style={{ color: 'var(--text-tertiary)', marginTop: 3 }} />
        Review annotations do not rewrite the GOVERN decision and cannot authorise execution.
      </span>
      <div style={{ display: 'flex', gap: 8 }}>
        <Button size="sm" onClick={onAnnotate}>Add annotation</Button>
        <Button size="sm" variant="ghost" onClick={() => onToast('Evidence requested', c.id + ' · recorded in the trail')}>Request more evidence</Button>
        <Button size="sm" variant="ghost" onClick={() => onToast('Policy flagged for owner', 'policy ' + c.policy)}>Flag policy</Button>
      </div>
      {c.notes.length ? (
        <Disclosure label="Earlier annotations" count={c.notes.length}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {c.notes.map((n, i) => (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: '64ch' }}>
                <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>{n.who} · {n.when}</span>
                <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)', textWrap: 'pretty' }}>{n.text}</span>
              </div>
            ))}
          </div>
        </Disclosure>
      ) : null}
    </section>
  );
}

const EVENT = { intake: 'Case opened', agents: 'Agent positions received', conflict: 'Conflict detected', resolve: 'Options resolved', weigh: 'Scoring completed', govern: 'GOVERN decided', executor: 'Executor', reviewer: 'Annotation recorded' };

function AuditSection({ c }) {
  const recent = c.audit.slice().reverse().slice(0, 4);
  return (
    <section style={{ marginTop: 32, paddingTop: 18, borderTop: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: 12 }}>
      <span style={{ font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Audit trail</span>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
        {recent.map((e, i) => (
          <div key={i} style={{ display: 'grid', gridTemplateColumns: '96px minmax(0,1fr)', gap: 20, alignItems: 'baseline' }}>
            <span data-numeric style={{ font: 'var(--type-mono)', color: 'var(--text-secondary)' }}>{String(e.time).slice(0, 8)}</span>
            <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)' }}>
              {e.actor === 'govern' || e.actor === 'executor' ? `${EVENT[e.actor]} — ${e.message.toLowerCase()}` : EVENT[e.actor] || e.message}
            </span>
          </div>
        ))}
      </div>
      <Disclosure label="Show full audit trail" count={c.audit.length}>
        <AuditTrail entries={c.audit} />
      </Disclosure>
    </section>
  );
}

function DecisionRecord({ c, onBack, onToast }) {
  const [dialog, setDialog] = React.useState(false);
  const s = STATE[c.status] || STATE.allowed;
  const chose = c.candidates.find((o) => o.verdict === 'chosen') || c.candidates[0];
  const inReview = c.stages.some((st) => st.label === 'Review' && st.state === 'active');
  const toast = (title, detail) => onToast({ tone: 'neutral', title, detail });
  const govMark = c.status === 'blocked' ? 'stop' : c.status === 'escalated' ? 'hold' : 'none';

  return (
    <div style={{ overflow: 'auto', height: '100%', position: 'relative' }}>
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '20px 28px 60px' }}>
        <button type="button" onClick={onBack}
          style={{ display: 'inline-flex', alignItems: 'center', gap: 7, border: 0, background: 'none', padding: 0, marginBottom: 20, cursor: 'pointer', color: 'var(--text-secondary)', font: 'var(--type-body-sm)' }}>
          <Icon name="arrow-left" size={13} /> Cases
        </button>

        {/* Case identity — quiet, never competing with the verdict */}
        <header style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <span style={{ font: 'var(--type-mono)', color: 'var(--text-secondary)' }}>{c.id}</span>
            <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)' }}>{c.domain} · {c.value}</span>
          </span>
          <h1 style={{ font: 'var(--fw-medium) 20px/1.25 var(--font-sans)', letterSpacing: '-0.018em', color: 'var(--text-primary)', maxWidth: '34ch' }}>{c.title}</h1>
        </header>

        <Verdict c={c} s={s} />

        <div style={{ display: 'flex', gap: 8, paddingBottom: 26, borderBottom: '1px solid var(--border-subtle)' }}>
          <Button icon="message-square-plus" onClick={() => setDialog(true)}>Annotate</Button>
          <Button variant="ghost" icon="refresh-cw" onClick={() => toast('Re-evaluation requested', c.id + ' · queued for GOVERN')}>Request re-evaluation</Button>
        </div>

        {/* How Sentinel got there */}
        <div style={{ paddingTop: 26 }}>
          <span style={{ display: 'inline-block', font: 'var(--type-label)', letterSpacing: 'var(--ls-label)', textTransform: 'uppercase', color: 'var(--text-tertiary)', paddingBottom: 18 }}>How Sentinel reached this</span>
          <Stage label="Agents" summary={`${c.agents} agent${c.agents === 1 ? '' : 's'} proposed a position on this action.`}>
            {c.positions.length ? <Disclosure label="Show positions" count={c.positions.length}><Positions positions={c.positions} /></Disclosure> : null}
          </Stage>
          <Stage label="Conflict" mark={c.positions.length ? 'split' : 'none'}
            summary={c.positions.length ? `Disagreed on ${c.conflictSubject.charAt(0).toLowerCase() + c.conflictSubject.slice(1)}.` : 'No disagreement — the agents returned the same position.'} />
          <Stage label="Resolve" summary={c.candidates.length === 1 ? 'A single viable option remained.' : `Reconciled into ${c.candidates.length} mutually exclusive options.`} />
          <Stage label="Weigh" summary={`“${chose.name}” scored highest at ${chose.score}.`}>
            <Disclosure label="Show scoring" count={c.candidates.length}><Scoring candidates={c.candidates} /></Disclosure>
          </Stage>
          <Stage label="Govern" mark={govMark} summary={`Evaluated “${chose.name}” against policy ${c.policy}.`}>
            <Disclosure label="Show governance reasoning">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 9, maxWidth: '64ch' }}>
                {c.reasons.map((r, i) => (
                  <div key={i} style={{ display: 'grid', gridTemplateColumns: '86px minmax(0,1fr)', gap: 20, paddingTop: 8, borderTop: '1px solid var(--border-hairline)' }}>
                    <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)' }}>{r.label}</span>
                    <span style={{ font: 'var(--type-body-sm)', color: 'var(--text-secondary)', textWrap: 'pretty' }}>{r.value}</span>
                  </div>
                ))}
                <span style={{ font: 'var(--type-mono)', color: 'var(--text-tertiary)' }}>decided by GOVERN · {c.opened} · {c.latency} end to end</span>
              </div>
            </Disclosure>
          </Stage>
          <Stage label="Executor" last mark={c.exec && c.exec.result.startsWith('Failed') ? 'stop' : 'none'}>
            <ExecutorBlock c={c} s={s} />
          </Stage>
        </div>

        {inReview ? <ReviewSection c={c} onAnnotate={() => setDialog(true)} onToast={toast} /> : null}
        <AuditSection c={c} />
      </div>

      <Dialog open={dialog} label="Human review" title="Add annotation"
        description="Appended to the audit trail. It does not change the GOVERN decision."
        onClose={() => setDialog(false)}
        footer={<><Button onClick={() => setDialog(false)}>Cancel</Button>
          <Button variant="primary" onClick={() => { setDialog(false); toast('Annotation recorded', c.id + ' · audit trail updated'); }}>Record note</Button></>}>
        <Textarea rows={4} placeholder="What should a future reviewer know?" counter="0/500" />
      </Dialog>
    </div>
  );
}

Object.assign(window, { DecisionRecord });
})();
