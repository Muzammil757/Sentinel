(() => {
const CASES = [
  { id: 'CASE-2041', title: 'Vendor payout above ceiling', status: 'blocked', conflict: true, surface: 'payouts.settle',
    amount: '₹18,40,000', time: '14:02', opened: '14:02:11.402 IST', policy: 'payout-v4', latency: '3.2s', agents: 2,
    chain: { agents:'passed', conflict:'conflict', resolve:'passed', weigh:'passed', govern:'blocked', executor:'halted' },
    chainDetail: 'halted at GOVERN · policy payout-v4',
    headline: 'Execution blocked before any external call.',
    reasons: [
      { label: 'Trigger', value: 'Requested amount exceeds the vendor ceiling by 41%.' },
      { label: 'Conflict', value: 'risk-agent and settlement-agent disagreed on reversibility within SLA.' },
      { label: 'Effect', value: 'No payout request was issued. Funds remain held.' },
    ],
    stages: [
      { label: 'Intake', state: 'done', detail: '14:02:11' }, { label: 'Weigh', state: 'done', detail: '3 candidates' },
      { label: 'Govern', state: 'blocked', detail: 'policy payout-v4' }, { label: 'Execution', state: 'skipped', detail: 'not reached' },
      { label: 'Review', state: 'active', detail: 'annotation open' },
    ],
    candidates: [
      { rank: '01', name: 'Hold payout for manual settlement', proposedBy: 'risk-agent v7', score: '0.82', verdict: 'chosen', rationale: 'Lowest exposure; reversible within SLA.' },
      { rank: '02', name: 'Release with partial amount', proposedBy: 'settlement-agent v3', score: '0.61', verdict: 'rejected', rationale: 'Still breaches the vendor ceiling policy.' },
      { rank: '03', name: 'Defer 6h and re-evaluate', proposedBy: 'risk-agent v7', score: '0.44', verdict: 'considered', rationale: 'Reversal window closes before the next evaluation.' },
    ],
    conflictSubject: 'Reversibility of the payout within SLA',
    positions: [
      { agent: 'risk-agent v7', position: 'Hold', basis: 'Vendor ceiling breached; counterparty unseen for 90 days.', confidence: '0.82' },
      { agent: 'settlement-agent v3', position: 'Release', basis: 'Reversal window open for a further 6 hours.', confidence: '0.61' },
    ],
    audit: [
      { time: '14:02:11.402', actor: 'intake', actorKind: 'system', message: 'Case opened from payout webhook', detail: 'src payouts.settle' },
      { time: '14:02:12.118', actor: 'agents', actorKind: 'agent', message: 'risk-agent v7 proposed 2 options' },
      { time: '14:02:13.907', actor: 'conflict', actorKind: 'agent', message: 'Conflict detected between 2 agents', detail: 'subject reversibility' },
      { time: '14:02:13.988', actor: 'resolve', actorKind: 'agent', message: 'Positions reconciled into 3 candidates' },
      { time: '14:02:14.061', actor: 'weigh', actorKind: 'agent', message: 'Scored 3 candidates', detail: 'top 0.82' },
      { time: '14:02:14.118', actor: 'govern', actorKind: 'govern', message: 'Blocked', detail: 'policy payout-v4 · rule ceiling.vendor' },
      { time: '14:02:14.121', actor: 'executor', actorKind: 'execution', message: 'No call issued', detail: 'stage halted' },
      { time: '14:04:02.220', actor: 'reviewer', actorKind: 'reviewer', message: 'Annotation recorded', detail: 'no authority change' },
    ],
    notes: [{ who: 'p.rao', when: '14:04', text: 'Vendor ceiling is stale — finance raised it last quarter. Flagged to the policy owner.' }],
    exec: null },

  { id: 'CASE-2043', title: 'Vendor onboarding KYC mismatch', status: 'escalated', conflict: true, surface: 'onboarding.activate',
    amount: '—', time: '13:41', opened: '13:41:19.220 IST', policy: 'kyc-v9', latency: '2.8s', agents: 2,
    chain: { agents:'passed', conflict:'conflict', resolve:'passed', weigh:'passed', govern:'escalated', executor:'halted' },
    chainDetail: 'escalated at GOVERN · awaiting review',
    headline: 'Escalated for human review before any activation.',
    reasons: [
      { label: 'Trigger', value: 'Registered name differs from the bank beneficiary name.' },
      { label: 'Conflict', value: 'kyc-agent and docs-agent disagreed on match confidence.' },
      { label: 'Effect', value: 'Activation held. No payout capability granted.' },
    ],
    stages: [
      { label: 'Intake', state: 'done', detail: '13:41:19' }, { label: 'Weigh', state: 'done', detail: '2 candidates' },
      { label: 'Govern', state: 'halted', detail: 'escalated' }, { label: 'Execution', state: 'pending', detail: 'held' },
      { label: 'Review', state: 'active', detail: '2 notes' },
    ],
    candidates: [
      { rank: '01', name: 'Hold activation pending document review', proposedBy: 'kyc-agent v4', score: '0.74', verdict: 'chosen', rationale: 'Name mismatch outside tolerance.' },
      { rank: '02', name: 'Activate with limited payout cap', proposedBy: 'docs-agent v2', score: '0.58', verdict: 'rejected', rationale: 'Not permitted for unverified beneficiaries.' },
    ],
    conflictSubject: 'Confidence of the beneficiary name match',
    positions: [
      { agent: 'kyc-agent v4', position: 'Hold', basis: 'Fuzzy name match 0.71 — below the 0.85 threshold.', confidence: '0.74' },
      { agent: 'docs-agent v2', position: 'Activate capped', basis: 'Registration certificate and PAN agree.', confidence: '0.58' },
    ],
    audit: [
      { time: '13:41:19.220', actor: 'intake', actorKind: 'system', message: 'Case opened from onboarding submission' },
      { time: '13:41:21.884', actor: 'conflict', actorKind: 'agent', message: 'Conflict detected between 2 agents' },
      { time: '13:41:22.017', actor: 'govern', actorKind: 'govern', message: 'Escalated', detail: 'policy kyc-v9 · rule name.match' },
    ],
    notes: [
      { who: 'a.mehta', when: '13:52', text: 'Beneficiary name matches the parent entity, not the registered vendor. Documents requested.' },
      { who: 'p.rao', when: '14:01', text: 'Second document received; still awaiting bank confirmation.' },
    ],
    exec: null },

  { id: 'CASE-2044', title: 'Settlement webhook replay', status: 'failed', surface: 'settlements.replay',
    amount: '₹6,12,400', time: '12:20', opened: '12:20:44.010 IST', policy: 'settle-v1', latency: '1.9s', agents: 1,
    chain: { agents:'passed', conflict:'clear', resolve:'passed', weigh:'passed', govern:'passed', executor:'blocked' },
    chainDetail: 'execution failed · HTTP 503 upstream',
    headline: 'Allowed by GOVERN; execution failed at the downstream API.',
    reasons: [
      { label: 'Trigger', value: 'Replay of 3 settlement webhooks after a partner outage.' },
      { label: 'Failure', value: 'Partner returned 503 on attempt 2 of 3; no partial state written.' },
      { label: 'Effect', value: 'Case held for re-evaluation. No automatic retry.' },
    ],
    stages: [
      { label: 'Intake', state: 'done', detail: '12:20:44' }, { label: 'Weigh', state: 'done', detail: '1 candidate' },
      { label: 'Govern', state: 'done', detail: 'allowed' }, { label: 'Execution', state: 'blocked', detail: '503 upstream' },
      { label: 'Review', state: 'active', detail: 'annotation open' },
    ],
    candidates: [{ rank: '01', name: 'Replay all 3 webhooks', proposedBy: 'settlement-agent v3', score: '0.88', verdict: 'chosen', rationale: 'Idempotent; partner reported recovery.' }],
    conflictSubject: null, positions: [],
    audit: [
      { time: '12:20:44.010', actor: 'intake', actorKind: 'system', message: 'Case opened from partner recovery signal' },
      { time: '12:20:45.332', actor: 'govern', actorKind: 'govern', message: 'Allowed', detail: 'policy settle-v1' },
      { time: '12:20:46.901', actor: 'executor', actorKind: 'execution', message: 'Failed on attempt 2/3', detail: 'HTTP 503 · no partial write' },
    ],
    notes: [], exec: { id: 'EXEC-8830', target: 'settlements.replay', duration: '1.9s', result: 'Failed · HTTP 503', at: '12:20:46 IST' } },

  { id: 'CASE-2042', title: 'Refund batch retry', status: 'allowed', surface: 'refunds.batch.retry',
    amount: '₹42,900', time: '13:58', opened: '13:58:02.004 IST', policy: 'refund-v2', latency: '1.4s', agents: 1,
    chain: { agents:'passed', conflict:'clear', resolve:'passed', weigh:'passed', govern:'passed', executor:'passed' },
    chainDetail: 'executed · 412ms · 14/14',
    headline: 'Execution allowed and completed on the first attempt.',
    reasons: [
      { label: 'Trigger', value: 'Retry of 14 refunds failed by an upstream timeout.' },
      { label: 'Basis', value: 'All amounts inside per-item and batch ceilings.' },
    ],
    stages: [
      { label: 'Intake', state: 'done', detail: '13:58:02' }, { label: 'Weigh', state: 'done', detail: '2 candidates' },
      { label: 'Govern', state: 'done', detail: 'allowed' }, { label: 'Execution', state: 'done', detail: '412ms · 14/14' },
      { label: 'Review', state: 'skipped', detail: 'not required' },
    ],
    candidates: [
      { rank: '01', name: 'Retry all 14 refunds now', proposedBy: 'settlement-agent v3', score: '0.91', verdict: 'chosen', rationale: 'Upstream healthy for 6 minutes.' },
      { rank: '02', name: 'Stagger retries over 10 minutes', proposedBy: 'settlement-agent v3', score: '0.55', verdict: 'rejected', rationale: 'Breaches the customer refund SLA.' },
    ],
    conflictSubject: null, positions: [],
    audit: [
      { time: '13:58:02.004', actor: 'intake', actorKind: 'system', message: 'Case opened from retry scheduler' },
      { time: '13:58:03.551', actor: 'govern', actorKind: 'govern', message: 'Allowed', detail: 'policy refund-v2' },
      { time: '13:58:03.963', actor: 'executor', actorKind: 'execution', message: 'Completed 14/14', detail: 'EXEC-8841 · 412ms' },
    ],
    notes: [], exec: { id: 'EXEC-8841', target: 'refunds.batch.retry', duration: '412ms', result: '14 of 14 succeeded', at: '13:58:03 IST' } },
];

const CHAIN_THROUGHPUT = [
  { link: 'Agents', value: 412, note: 'proposals · 24h' },
  { link: 'Conflict', value: 38, note: 'disagreements' },
  { link: 'Resolve', value: 38, note: 'reconciled' },
  { link: 'Weigh', value: 412, note: 'candidate sets scored' },
  { link: 'Govern', value: 412, note: '396 allowed · 12 blocked · 4 escalated' },
  { link: 'Executor', value: 396, note: '394 succeeded · 2 failed' },
];

const RELIABILITY = [
  { label: 'Execution success', value: 99.4, target: 'target 99.5% · trailing 30d', tone: 'allowed' },
  { label: 'Govern latency budget', value: 82, target: 'p99 118ms of 150ms', tone: 'escalated' },
  { label: 'Agent agreement', value: 64, target: '12 conflicts today', tone: 'blocked' },
  { label: 'Audit completeness', value: 100, target: 'no gaps in 30d', tone: 'allowed' },
];

const EXECUTORS = [
  { region: 'ap-south-1', state: 'allowed', depth: '0', last: '412ms', note: 'Healthy' },
  { region: 'eu-west-1', state: 'allowed', depth: '2', last: '388ms', note: 'Healthy' },
  { region: 'us-east-1', state: 'escalated', depth: '9', last: '1.9s', note: 'Partner 503s' },
];

const GLOBAL_AUDIT = [
  { time: '14:04:02.220', actor: 'reviewer', actorKind: 'reviewer', message: 'Annotation recorded on CASE-2041', detail: 'p.rao · no authority change' },
  { time: '14:02:14.118', actor: 'govern', actorKind: 'govern', message: 'Blocked CASE-2041', detail: 'policy payout-v4 · rule ceiling.vendor' },
  { time: '14:02:13.907', actor: 'conflict', actorKind: 'agent', message: 'Conflict detected · CASE-2041', detail: '2 agents · reversibility' },
  { time: '13:58:03.963', actor: 'executor', actorKind: 'execution', message: 'Completed EXEC-8841', detail: '412ms · ap-south-1' },
  { time: '13:58:03.551', actor: 'govern', actorKind: 'govern', message: 'Allowed CASE-2042', detail: 'policy refund-v2' },
  { time: '13:41:22.017', actor: 'govern', actorKind: 'govern', message: 'Escalated CASE-2043', detail: 'policy kyc-v9 · rule name.match' },
  { time: '12:20:46.901', actor: 'executor', actorKind: 'execution', message: 'Failed EXEC-8830', detail: 'HTTP 503 · us-east-1' },
  { time: '12:20:45.332', actor: 'govern', actorKind: 'govern', message: 'Allowed CASE-2044', detail: 'policy settle-v1' },
  { time: '11:04:00.000', actor: 'system', actorKind: 'system', message: 'Policy bundle deployed', detail: '18 policies · rev 214' },
];

const SCENARIO = [
  { t: '00.0s', link: 'Agents', title: 'Three agents propose', body: 'risk-agent, settlement-agent and ledger-agent each return a position on a ₹18.4L vendor payout.', chain: { agents:'active' } },
  { t: '01.7s', link: 'Conflict', title: 'Positions disagree', body: 'risk-agent says hold; settlement-agent says release. The disagreement is on reversibility, not on the amount.', chain: { agents:'passed', conflict:'active' } },
  { t: '01.8s', link: 'Resolve', title: 'Disagreement reconciled', body: 'Positions collapse into three mutually exclusive candidate options — no agent wins by rank.', chain: { agents:'passed', conflict:'conflict', resolve:'active' } },
  { t: '02.4s', link: 'Weigh', title: 'Candidates scored', body: 'Each option is scored on exposure, reversibility and SLA. Highest score: hold for manual settlement at 0.82.', chain: { agents:'passed', conflict:'conflict', resolve:'passed', weigh:'active' } },
  { t: '03.2s', link: 'Govern', title: 'GOVERN blocks', body: 'Policy payout-v4 rule ceiling.vendor is breached by 41%. The decision is blocked, with reasons recorded.', chain: { agents:'passed', conflict:'conflict', resolve:'passed', weigh:'passed', govern:'active' } },
  { t: '03.2s', link: 'Executor', title: 'Nothing executes', body: 'The executor is never called. No payout request leaves the control plane; the case routes to human review for annotation.', chain: { agents:'passed', conflict:'conflict', resolve:'passed', weigh:'passed', govern:'blocked', executor:'halted' } },
];

/* Level-1 summary fields: what an operator needs before opening the case. */
const SUMMARY = {
  'CASE-2041': { domain: 'Payouts', value: '₹18.4L', shortReason: 'Vendor ceiling exceeded by 41%' },
  'CASE-2043': { domain: 'Onboarding', value: 'KYC', shortReason: 'Beneficiary name outside match tolerance' },
  'CASE-2044': { domain: 'Settlements', value: '₹6.1L', shortReason: 'Partner returned 503 mid-replay' },
  'CASE-2042': { domain: 'Refunds', value: '₹42.9K', shortReason: 'Inside all ceilings' },
};
CASES.forEach((c) => Object.assign(c, SUMMARY[c.id]));

Object.assign(window, { CASES, CHAIN_THROUGHPUT, RELIABILITY, EXECUTORS, GLOBAL_AUDIT, SCENARIO });
})();
