(() => {
/*
 * Real-data adapter, replacing the original Data.jsx's hardcoded fixture
 * cases. Cases.jsx, DecisionRecord.jsx, Primitives.jsx and
 * Shell.jsx are byte-identical to the design export -- this file's only job
 * is to produce the exact same shape those files already expect, filled
 * from GET /api/cases and GET /api/cases/{id} on the real FastAPI backend
 * instead of from a literal array. Nothing here computes a score, rank,
 * outcome or authorization -- every value is copied from what the pipeline
 * already decided, real API data only. See README-DATA-ADAPTER notes
 * inline for each field's provenance.
 *
 * The design's own vocabulary is a 4-state model (blocked/escalated/failed/
 * allowed) that predates this backend and doesn't have a clean 1:1 mapping
 * from Sentinel's real GOVERN outcomes (PROCEED/HOLD/ESCALATE/AMBIGUOUS) or
 * EXECUTOR status (EXECUTED/REJECTED). mapStatus() below documents the
 * chosen mapping; it is an approximation, not a re-derivation of GOVERN's
 * decision -- GOVERN's own real outcome/execution_authorized values are
 * still carried through untouched in every case's `reasons`/`policy` fields.
 *
 * Cases whose latest run never reached RESOLVE (no persisted candidates --
 * i.e. a pipeline failure before WEIGH/GOVERN ever ran) are left out of the
 * mapped list entirely: DecisionRecord.jsx assumes at least one candidate
 * exists, and inventing a placeholder candidate to avoid a crash would mean
 * fabricating data, which this adapter does not do.
 */

const API_BASE = '/api';

// Same denylist app.js has used throughout this project: historical
// connectivity-verification artifacts, not demo/production data. Named by
// stable external_case_id, never an internal UUID.
const HIDDEN_EXTERNAL_CASE_IDS = new Set([
  'sentinel-live-verify-001',
  'sentinel-live-verify-rejected-001',
  'sentinel-live-verify-failed-001',
]);

async function apiGet(path) {
  const response = await fetch(`${API_BASE}${path}`, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`GET ${path} failed: HTTP ${response.status}`);
  return response.json();
}

function fmtClock(iso) {
  if (!iso) return '--';
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
  } catch {
    return '--';
  }
}

function fmtOpened(iso) {
  if (!iso) return '--';
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour12: false }) + '.' + String(d.getMilliseconds()).padStart(3, '0');
  } catch {
    return '--';
  }
}

function fmtLatency(startIso, endIso) {
  if (!startIso || !endIso) return '--';
  const ms = new Date(endIso).getTime() - new Date(startIso).getTime();
  if (!Number.isFinite(ms) || ms < 0) return '--';
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
}

// GOVERN's real outcome vocabulary (PROCEED/HOLD/ESCALATE/AMBIGUOUS) and
// EXECUTOR's (EXECUTED/REJECTED) mapped onto the design's 4-state model.
// See the file header for why this is an approximation, not a re-decision.
function mapStatus(run, govern, receipt) {
  if (run.status === 'FAILED') return 'failed';
  if (!govern) return 'escalated';
  if (govern.outcome === 'PROCEED') {
    return receipt && receipt.status === 'REJECTED' ? 'failed' : 'allowed';
  }
  return 'escalated'; // HOLD, ESCALATE, AMBIGUOUS all route to a human -- "escalated" is the closest single word the design has.
}

const DOMAIN_LABEL = { payouts: 'Payouts', dispute: 'Disputes', rto: 'RTO', retention: 'Retention' };

function findAmount(agents) {
  for (const a of agents) {
    const payload = a.payload || {};
    if (typeof payload.amount === 'number') return payload.amount;
    if (typeof payload.disputed_amount === 'number') return payload.disputed_amount;
  }
  return null;
}

// audit_events.stage -> AuditTrail's {actor, actorKind} vocabulary (see
// components/governance/AuditTrail.jsx and DecisionRecord.jsx's EVENT map).
const STAGE_ACTOR = {
  RUN_STARTED: ['intake', 'system'],
  AGENTS_RECORDED: ['agents', 'agent'],
  CONFLICT_EVALUATED: ['conflict', 'agent'],
  RESOLVE_COMPLETED: ['resolve', 'agent'],
  WEIGH_COMPLETED: ['weigh', 'agent'],
  GOVERN_DECIDED: ['govern', 'govern'],
  EXECUTOR_COMPLETED: ['executor', 'execution'],
  RUN_FAILED: ['system', 'system'],
};

function mapAudit(timelineEvents, humanReviews) {
  const fromEvents = timelineEvents.map((e) => {
    const [actor, actorKind] = STAGE_ACTOR[e.stage] || ['system', 'system'];
    let detail;
    if (e.detail) detail = typeof e.detail === 'string' ? e.detail : JSON.stringify(e.detail);
    return { time: fmtOpened(e.occurred_at), actor, actorKind, message: e.summary, detail };
  });
  const fromReviews = humanReviews.map((r) => ({
    time: fmtOpened(r.created_at),
    actor: 'reviewer',
    actorKind: 'reviewer',
    message: `Annotation recorded (${r.action})`,
    detail: r.reason || undefined,
  }));
  return fromEvents.concat(fromReviews).sort((a, b) => (a.time > b.time ? 1 : -1));
}

function mapCandidates(candidates, govern) {
  return candidates
    .slice()
    .sort((a, b) => (a.score ? a.score.rank : 99) - (b.score ? b.score.rank : 99))
    .map((c) => {
      const s = c.score;
      const chosen = govern && govern.selected_candidate_row_id === c.id;
      const verdict = chosen ? 'chosen' : s && s.eligible === false ? 'rejected' : 'considered';
      return {
        rank: s ? String(s.rank).padStart(2, '0') : '--',
        // RESOLVE's own internal id for this candidate (e.g.
        // "defer_to_agent-1") -- the exact string GOVERN's real
        // rationale.outcome_sentence quotes when it names the winning
        // candidate. `name` below is the human-readable resulting action
        // ("HOLD_RELATED_ACTIONS"); both refer to the same real candidate,
        // but without candidateId displayed somewhere, GOVERN's headline
        // and the Weigh/Resolve candidate list have no visible link between
        // them, and a reader has no way to confirm they're the same thing.
        candidateId: c.candidate_id,
        name: (c.resulting_actions && c.resulting_actions.length ? c.resulting_actions.join(', ') : c.strategy),
        proposedBy: c.preferred_agent || c.strategy,
        score: s ? s.total_score.toFixed(2) : '0.00',
        verdict,
        rationale: c.rationale,
      };
    });
}

function mapPositions(conflict, agents) {
  if (!conflict || !conflict.conflict) return [];
  return agents
    .filter((a) => a.role === 'agent_a' || a.role === 'agent_b')
    .map((a) => ({
      agent: a.agent_name,
      position: a.proposed_action,
      basis: `Proposed ${a.proposed_action} at confidence ${Number(a.confidence).toFixed(2)}.`,
      confidence: Number(a.confidence).toFixed(2),
    }));
}

function mapExec(receipt, timelineEvents) {
  if (!receipt) return null;
  const governedAt = (timelineEvents.find((e) => e.stage === 'GOVERN_DECIDED') || {}).occurred_at;
  const executedAt = (timelineEvents.find((e) => e.stage === 'EXECUTOR_COMPLETED') || {}).occurred_at;
  const result =
    receipt.status === 'EXECUTED'
      ? `${(receipt.executed_actions || []).length} action(s) executed`
      : `Failed · ${(receipt.rejection && receipt.rejection.reason) || 'rejected by EXECUTOR'}`;
  return {
    id: receipt.receipt_id.slice(0, 16),
    target: (receipt.authorization && receipt.authorization.authorized_actions && receipt.authorization.authorized_actions.join(', ')) || '--',
    duration: fmtLatency(governedAt, executedAt),
    result,
    at: fmtOpened(executedAt),
    // Real, itemized action detail (DecisionRecord's "authorized vs
    // executed" comparison) -- each entry is exactly what
    // executor/actions.py's mock execution recorded, never inferred.
    executedActions: (receipt.executed_actions || []).map((a) => a.action || a.effect || JSON.stringify(a)),
    rejectionReason: (receipt.rejection && receipt.rejection.reason) || null,
  };
}

async function mapCase(summary) {
  const detail = await apiGet(`/cases/${encodeURIComponent(summary.case_id)}`);
  const { run, agents = [], conflict, candidates = [], govern_result: govern, execution_receipt: receipt, timeline = [], human_reviews: humanReviews = [] } = detail;

  if (!run || candidates.length === 0) {
    // No RESOLVE output ever persisted for this run (pipeline failed before
    // WEIGH/GOVERN). DecisionRecord.jsx assumes at least one candidate;
    // rather than invent one, this case is left out of the mapped list.
    console.info(`[Data.jsx] skipping ${summary.external_case_id || summary.case_id}: no persisted candidates`);
    return null;
  }
  if (!govern) {
    // Candidates exist (RESOLVE ran) but WEIGH/GOVERN never produced a
    // decision -- a real, if rare, failure mode (e.g. WEIGH itself raised).
    // DecisionRecord's case header/GOVERN/EXECUTOR sections all assume a
    // real GOVERN outcome exists; skip rather than show a blank verdict.
    console.info(`[Data.jsx] skipping ${summary.external_case_id || summary.case_id}: no persisted GOVERN result`);
    return null;
  }

  const status = mapStatus(run, govern, receipt);
  const amount = findAmount(agents);
  const topScore = candidates.reduce((best, c) => (c.score && (!best || c.score.total_score > best) ? c.score.total_score : best), null);
  const humanReviewRequired = !!summary.human_review_required;
  const whyText = (govern && govern.rationale && govern.rationale.outcome_sentence) || (govern && govern.outcome_basis) || run.status;

  return {
    id: summary.external_case_id || summary.case_id,
    title: conflict ? `${conflict.action_a} vs ${conflict.action_b}` : `${run.agent_a} vs ${run.agent_b}`,
    status,
    conflict: !!(conflict && conflict.conflict),
    surface: run.entity_type,
    amount: amount != null ? `₹${amount.toLocaleString('en-IN')}` : (topScore != null ? `score ${topScore.toFixed(2)}` : '--'),
    time: fmtClock(run.created_at),
    opened: fmtOpened(run.created_at),
    policy: run.policy_id,
    latency: fmtLatency(run.created_at, (timeline.find((e) => e.stage === 'EXECUTOR_COMPLETED') || timeline.find((e) => e.stage === 'GOVERN_DECIDED') || {}).occurred_at),
    agents: agents.length,
    // Real GOVERN/EXECUTOR vocabulary, passed through untouched alongside
    // the design's approximated `status` word above -- DecisionRecord's
    // case header, GOVERN section and EXECUTOR section read these directly
    // rather than re-deriving anything from `status`. governOutcome is
    // always one of PROCEED/HOLD/ESCALATE/AMBIGUOUS here: a case only
    // reaches this point (see the candidates.length guard above) if GOVERN
    // actually ran, so this is never null for a mapped case.
    governOutcome: govern.outcome,
    executionAuthorized: !!govern.execution_authorized,
    policyVersion: run.policy_version,
    policyHash: run.policy_hash,
    authorizedActions: (govern.authorized_actions || []).slice(),
    receiptStatus: receipt ? receipt.status : null,
    chainDetail: whyText,
    headline: whyText,
    reasons: [{ label: status === 'allowed' ? 'Basis' : 'Failure', value: whyText }].concat(
      govern && govern.rationale && Array.isArray(govern.rationale.reasons)
        ? govern.rationale.reasons.map((code) => ({ label: 'Reason', value: code }))
        : []
    ),
    stages: [
      { label: 'Intake', state: 'done', detail: fmtClock(run.created_at) },
      { label: 'Weigh', state: 'done', detail: `${candidates.length} candidate${candidates.length === 1 ? '' : 's'}` },
      { label: 'Govern', state: govern ? (status === 'allowed' ? 'done' : status === 'failed' ? 'blocked' : 'halted') : 'skipped', detail: govern ? govern.outcome : 'not reached' },
      { label: 'Execution', state: !receipt ? 'skipped' : receipt.status === 'EXECUTED' ? 'done' : 'blocked', detail: receipt ? receipt.status : 'not reached' },
      { label: 'Review', state: humanReviewRequired ? 'active' : 'skipped', detail: humanReviewRequired ? 'annotation open' : 'not required' },
    ],
    candidates: mapCandidates(candidates, govern),
    conflictSubject: conflict && conflict.conflict ? conflict.reason : null,
    positions: mapPositions(conflict, agents),
    audit: mapAudit(timeline, humanReviews),
    notes: humanReviews.map((r) => ({ who: r.reviewer || 'unknown', when: fmtClock(r.created_at), text: r.reason || `action: ${r.action}` })),
    exec: mapExec(receipt, timeline),
    domain: DOMAIN_LABEL[run.agent_a] || DOMAIN_LABEL[run.agent_b] || run.entity_type,
    value: amount != null ? `₹${amount.toLocaleString('en-IN')}` : topScore != null ? topScore.toFixed(2) : '--',
    shortReason: (conflict && conflict.reason) || whyText,
  };
}

// Real cases only -- GET /api/cases is a truthful, complete persistence
// read; the denylist above only decides what this UI renders, exactly as
// the previous vanilla frontend did.
window.loadSentinelData = async function loadSentinelData() {
  const summaries = await apiGet('/cases');
  const visible = summaries.filter((c) => !HIDDEN_EXTERNAL_CASE_IDS.has(c.external_case_id));
  // Sequential, not Promise.all: each case detail fetch is itself several
  // sequential Supabase round trips server-side, and firing many of those
  // fans in parallel is more concurrent load than this backend's Supabase
  // client reliably handles. One case at a time is slower but robust.
  const cases = [];
  for (const summary of visible) {
    try {
      const mapped = await mapCase(summary);
      if (mapped) cases.push(mapped);
    } catch (err) {
      console.error(`[Data.jsx] failed to load case ${summary.case_id}:`, err);
    }
  }
  Object.assign(window, { CASES: cases });
  return cases;
};
})();
