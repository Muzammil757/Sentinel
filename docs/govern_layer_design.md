# Sentinel — GOVERN Layer Architecture Design

**Status:** Design only. Not implemented. Nothing in `backend/` was created or modified for this task.
**Phase:** 2C (follows 2B WEIGH, commit `985d430`)
**Audience:** the engineer implementing `backend/govern/`
**Rule for the implementer:** every architectural decision needed to write this layer is fixed below. If you hit a decision this document does not answer, stop and escalate rather than inventing one.

---

## 0. Reading notes and grounding

This design was written against the code as it exists at `985d430`, with **148 tests passing**. Every number in §S was produced by running the real pipeline (`conflict_matrix` → `resolve` → `weigh`) against `backend/policy/policy_bundle.yaml` (`policy_hash` prefix `9632ad23…`) — none is estimated.

| Component | File | What GOVERN depends on |
|---|---|---|
| Agents | `backend/mock_agents/*.py` | `agent`, `proposed_action`, `confidence`, `amount`, `dispute_status` |
| Conflict Matrix | `backend/conflict_matrix/matrix.py` | which action pairs conflict |
| RESOLVE | `backend/resolve/resolver.py`, `rules.py` | `strategy`, `preferred_agent`, `resulting_actions`, `unresolved` |
| WEIGH | `backend/weigh/*.py` | `candidates[]`, `ranking[]`, `ambiguity`, `constraint_evaluation`, `total_score`, `profile.profile_name` |
| Policy | `backend/policy/policy_bundle.yaml`, `loader.py` | `escalation`, `authority`, `claude`, `fallback`, `audit`, `hard_constraints` |

**Pipeline position (unchanged):**

```
Agents → Conflict Matrix → RESOLVE → WEIGH → GOVERN → Action Executor → Audit Receipt
```

**Three field-name traps verified in the code, listed here because each one will silently break an implementation:**

1. WEIGH emits `profile.profile_name`, **not** `profile.selected` — `"selected"` is on `weigh.schema.FORBIDDEN_OUTPUT_KEYS` and a recursive test asserts its absence. The audit field is *named* `profile_selected`; its *source* is `profile.profile_name`.
2. `authority.actions_requiring_escalation: [HOLD_BOTH_PENDING_REVIEW]` names a RESOLVE **strategy**, not an action. Matching it against `resulting_actions` alone matches nothing, ever.
3. `fallback.*` uses the token `HOLD_FOR_REVIEW`, which is **not** a member of `escalation.outcomes: [PROCEED, HOLD, ESCALATE, AMBIGUOUS]`. An implementation that assigns a fallback value straight into `outcome` emits an outcome the policy does not define.

---

## A. GOVERN's responsibility

GOVERN is the **only** layer that names a winner and the **only** layer that authorizes execution. It answers one question:

> Given WEIGH's comparison, which candidate — if any — is *actually permitted to execute* under this policy, and what is the case's governance outcome?

Concretely it must:

1. Consume WEIGH output plus the raw evidence WEIGH consumed (`agent_actions`, `case_context`, `policy`).
2. **Independently re-derive** every hard-constraint status from raw evidence, never trusting WEIGH's advisory findings.
3. **Enforce** authority — the two policy lists (`actions_requiring_governance`, `actions_requiring_escalation`) that WEIGH never reads at all, plus per-agent limits.
4. Compute the **permitted set**: candidates that survive both of the above.
5. **Order the permitted set using WEIGH's existing `total_score`.** Never recompute a score.
6. Assign exactly one outcome from `escalation.outcomes` via a fixed decision table.
7. Derive `execution_authorized` as a single boolean, and the `authorized_actions` list.
8. Optionally consult a **bounded, injected** Claude advisor — and produce byte-identical `execution_authorized` and `decision_id` whether that advisor is present, absent, or failing.
9. Emit every audit field `policy.audit.required_fields` asks of it.

---

## B. Non-responsibilities

GOVERN must not:

| Must not | Why / where it belongs |
|---|---|
| Re-score, re-weight, or re-rank by any number it computed itself | WEIGH owns comparative scoring (§C.2) |
| Recompute objective impacts, contributions, or `total_score` | WEIGH; GOVERN reads them verbatim |
| Recompute ambiguity signals or near-tie membership | WEIGH; GOVERN reads `ambiguity` |
| Invent, merge, split, reword, or drop a candidate | RESOLVE owns candidate generation |
| Execute an action, write to the database, or call the network | Action Executor / orchestrator |
| Import an Anthropic SDK, or any HTTP client | Claude arrives as an injected port (§L) |
| Let Claude change `outcome` toward permissiveness, `execution_authorized`, `selected_candidate`, or the permitted set | §L.4 — enforced structurally |
| Read the clock, use randomness, or emit a timestamp | Orchestrator supplies `timestamp` (§P) |
| Estimate risk from `rto_score`, `churn_risk`, `disputed_amount`, `days_overdue` | The Open Track boundary, inherited from WEIGH §T |
| Short-circuit permission evaluation for *any* case, including no-conflict | §C.3 — the single most important rule in this document |
| Hard-code a threshold, band, or outcome that policy should own | §I, §R.1 |

---

## C. The WEIGH → GOVERN contract

### C.1 Signature

```python
govern.decide(
    weigh_output: dict,     # verbatim from weigh.evaluate_candidates
    agent_actions: dict,    # the SAME mapping passed to WEIGH
    case_context: dict,     # the SAME mapping passed to WEIGH
    policy: dict,           # the SAME already-loaded, already-validated dict
    advisor=None,           # optional Advisor port (§L). None ⇒ NullAdvisor
) -> dict                   # govern_output (§E)
```

Four required inputs, one optional port. `advisor=None` is the default and the demo-safe path: with no advisor, GOVERN is pure deterministic arithmetic over policy data.

### C.2 GOVERN does not re-score — it re-permits

This is the WEIGH/GOVERN boundary, stated as two sentences that must both stay true:

> **WEIGH:** *which candidate looks best under policy?* — comparative scoring, ranking, ambiguity detection.
> **GOVERN:** *which candidate/action is actually allowed to execute?* — constraint enforcement, authority enforcement, outcome assignment.

Operationally:

- GOVERN **re-derives permission** (constraint statuses, authority facts) from raw evidence. That is not duplication of WEIGH's job; `weigh_output.constraint_evaluation.authority == "advisory_only"` and `rechecked_by == "GOVERN"` say WEIGH deliberately declined to enforce.
- GOVERN **does not re-derive preference**. Every score, rank, gap, and ambiguity signal in GOVERN's output is copied from `weigh_output`, and `permission_evaluation.ordering_source == "weigh.total_score"` records that.
- A test (§U.2 #7) walks GOVERN's output and asserts every number it contains is present verbatim in `weigh_output` or is a policy threshold. GOVERN has no arithmetic of its own beyond comparisons.

**Disagreement rule.** GOVERN's re-derived constraint status is compared against WEIGH's reported status per candidate per constraint. Blocked is the **union** of both. Any disagreement is itself blocking and forces `ESCALATE` (§F.1, D2). Two independent layers must both agree before anything executes.

### C.3 The no-conflict rule — corrected

The WEIGH design (§C.3) says *"GOVERN must short-circuit `case.conflict == false` before scoring thresholds apply."* Read literally as "skip governance", that sentence is a payout-release bypass: **the only path by which `RELEASE_PAYMENT` reaches GOVERN today is `NO_CONFLICT_PROCEED`** (RESOLVE's `AGENT_PRIORITY_ORDER = [dispute, rto, payouts, retention]` guarantees `payouts` never wins a `DEFER_TO_AGENT`). A short-circuit on `conflict == false` would therefore short-circuit the *only* money-moving path in the system.

**The rule, corrected and binding:**

> On `case.conflict == false`, GOVERN skips **the score-band evaluation and nothing else**. Hard-constraint re-checks, authority enforcement, the governance gate, and the permitted-set computation all run exactly as they do for a conflict case.

The original reasoning survives intact and is *only* about the band: with a single candidate there is nothing to compare against, so `total_score` is not an absolute safety rating. The verified `NO_CONFLICT_PROCEED` score of **0.3100** sits below `hold_max_score` (0.40) for a perfectly benign release — and §S.3 shows that same 0.3100 producing `PROCEED` at ₹50 000 and `ESCALATE` at ₹50 001. The band was never what made that decision; authority was.

`authority.actions_requiring_governance: [RELEASE_PAYMENT, WIN_BACK_OFFER]` exists for exactly this, and §H.3 gives it operational teeth.

### C.4 Contract invariants (each is a test in §U)

1. **Candidate set is closed.** `{c.candidate_id}` in GOVERN output equals WEIGH's, which equals RESOLVE's. No additions, no removals.
2. **No re-scoring.** Every score in the output traces to `weigh_output`.
3. **Policy identity is consistent.** `compute_policy_hash(policy) == weigh_output.policy_hash`, or GOVERN raises. It must be impossible to enforce policy B against numbers produced under policy A.
4. **Exactly one outcome**, and it is a member of `policy.escalation.outcomes`.
5. **`execution_authorized` ⟺ `outcome == "PROCEED"`.** No other path sets it.
6. **Claude parity.** `execution_authorized` and `decision_id` are byte-identical across advisor present / absent / raising / timing-out / schema-violating.
7. **Purity.** Same five inputs (with a deterministic advisor) ⇒ byte-identical output.

---

## D. Input schema

### D.1 `weigh_output`

Consumed read-only. GOVERN requires these keys and raises `GovernInputError` if any is missing or malformed:

```
policy_id, policy_version, policy_hash,
case.{entity_type, agent_a, agent_b, conflict, unresolved}   # case_id optional
profile.{profile_name, weights}
evidence.{case_confidence, contributing_agents}
candidates[].{candidate_id, strategy, preferred_agent, resulting_actions,
              total_score, objective_impacts, constraint_findings,
              eligible, eligibility_basis, originating_confidence, evidence_complete}
ranking[].{candidate_id, rank, score_rank, total_score, eligible, tie_group}
ambiguity.{detected, signals, near_tie_group, top_gap}
constraint_evaluation.{authority, rechecked_by, constraints_checked,
                       violated_candidate_ids, indeterminate_candidate_ids}
```

Two structural assertions on arrival, both `GovernInputError`:

- `constraint_evaluation.authority == "advisory_only"` and `rechecked_by == "GOVERN"`. If a future WEIGH ever claimed enforcement authority, GOVERN must refuse to run rather than silently defer to it.
- `weigh_output` contains no key from `weigh.schema.FORBIDDEN_OUTPUT_KEYS` at any depth. GOVERN validates the layer above it rather than trusting it.

### D.2 `agent_actions`, `case_context`, `policy`

Identical objects to those passed to WEIGH — not reconstructions. GOVERN re-reads raw evidence (`dispute_status`, `proposed_action`, `amount`, `merchant_flags`) because a constraint re-check that reads WEIGH's `observed` block is not a re-check.

GOVERN never mutates any of the four.

### D.3 What GOVERN reads from policy

| Section | Use |
|---|---|
| `escalation.outcomes` | the closed set of legal outcomes; membership asserted |
| `escalation.thresholds` | `proceed_min_score`, `hold_max_score`, `mid_band_outcome` (§R.1) |
| `escalation.conditions` | prose; documentation only, never parsed |
| `authority.agents` | per-agent `autonomous_actions`, `max_autonomous_amount` |
| `authority.actions_requiring_governance` | the governance gate (§H.3) |
| `authority.actions_requiring_escalation` | matched against **strategy and actions** (§H.2) |
| `hard_constraints` | ids, `enforcement`, `parameters` for the re-check |
| `claude.*` | the four `may_*: false` invariants, asserted before any invocation |
| `fallback.*` | advisor failure handling, via the alias map (§N.1) |
| `audit.required_fields` | checked: GOVERN's output must supply every field it owns |
| `weights`, `scoring`, `objectives`, `profile_selection`, `ambiguity` | **not read.** Those are WEIGH's, and re-reading them is how re-scoring starts |

---

## E. Output schema

### E.1 Top level

```python
{
  "govern_version": "1.0.0",
  "decision_method": "policy_gated_v1",

  "policy_id": "sentinel_demo_policy_v1",
  "policy_version": "1.1.0",
  "policy_hash": "9632ad23…",
  "decision_id": "dec_a41f…",               # §P.2 — content hash, no clock, no uuid

  "case": { … },                            # echoed verbatim from weigh_output.case
  "profile_selected": "standard",           # from weigh_output.profile.profile_name
  "weights_used": { … },                    # echoed
  "objectives_considered": [ … ],           # sorted; keys of any objective_impacts

  "outcome": "PROCEED",                     # ∈ policy.escalation.outcomes
  "outcome_basis": "SCORE_AT_OR_ABOVE_PROCEED_MIN",
  "execution_authorized": true,
  "selected_candidate": { … } | null,       # non-null ONLY when outcome == "PROCEED"
  "authorized_actions": ["HOLD_RELATED_ACTIONS"],   # [] unless PROCEED
  "candidate_under_review": "defer_to_agent-1" | null,

  "score_band":            { … },           # §E.2
  "permission_evaluation": { … },           # §E.3
  "escalation":            { … },           # §E.4
  "claude":                { … },           # §E.5
  "rationale":             { … },           # §E.6
  "notes": [ … ]
}
```

`selected_candidate` and `candidate_under_review` are deliberately different fields. `selected_candidate` means *authorized to execute*, and is `null` for `HOLD` / `ESCALATE` / `AMBIGUOUS`. `candidate_under_review` is the top of the permitted order regardless of outcome, so the receipt and UI can say *"the option a human is being asked about"* without a reader mistaking it for a decision.

### E.2 `score_band`

```python
"score_band": {
  "evaluated": true,
  "reason_not_evaluated": null,             # "no_conflict_single_candidate" when skipped
  "score_source": "weigh.total_score",      # GOVERN never computes a score
  "evaluated_candidate_id": "defer_to_agent-1",
  "evaluated_score": 0.7500,                # copied, not computed
  "proceed_min_score": 0.75,
  "hold_max_score": 0.40,
  "mid_band_outcome": "HOLD",
  "band": "PROCEED_BAND"                    # PROCEED_BAND | MID_BAND | HOLD_BAND | null
}
```

### E.3 `permission_evaluation`

```python
"permission_evaluation": {
  "authority": "enforcing",                 # the counterpart to WEIGH's "advisory_only"
  "constraints_checked": ["HC_CONFIDENCE_FLOOR", … ],       # sorted
  "candidates": [
    {
      "candidate_id": "defer_to_agent-1",
      "strategy": "DEFER_TO_AGENT",
      "resulting_actions": ["HOLD_RELATED_ACTIONS"],
      "total_score": 0.7500,                # copied from weigh_output
      "score_rank": 1,                      # copied from weigh_output.ranking

      "constraint_recheck": [               # GOVERN's own, from raw evidence
        {"constraint_id": "HC_CONFIDENCE_FLOOR", "status": "SATISFIED",
         "observed": {"originating_confidence": 0.95, "min_confidence": 0.6},
         "weigh_status": "SATISFIED", "agrees": true}
      ],
      "authority": {                        # §H
        "per_action": {"HOLD_RELATED_ACTIONS": {"agent": "dispute", "result": "AUTHORIZED",
                                                "reason": "no_amount_limit"}},
        "requires_governance_actions": [],
        "requires_escalation": false,
        "escalation_match": null            # "strategy:HOLD_BOTH_PENDING_REVIEW" when matched
      },
      "governance_gate": null,              # §H.3; non-null when a gated action is present

      "permitted": true,
      "permission_basis": "all_checks_passed",
      "blocking_reasons": []                # e.g. ["HC_UNAUTHORIZED_ACTION:VIOLATED"]
    }
  ],
  "permitted_candidate_ids": ["defer_to_agent-1", "hold_both_pending_review-2"],
  "ordering_source": "weigh.total_score",
  "weigh_agreement": {"agreed": true, "disagreements": []}
}
```

`permitted_candidate_ids` is ordered by `(-total_score, candidate_id)` — WEIGH's score, GOVERN's filter.

### E.4 `escalation`

```python
"escalation": {
  "required": false,
  "reasons": [],                                   # stable machine codes, sorted
  "actions_requiring_governance_matched": ["RELEASE_PAYMENT"],
  "escalation_matches": []                         # ["strategy:HOLD_BOTH_PENDING_REVIEW"]
}
```

### E.5 `claude`

```python
"claude": {
  "gate": {"eligible": false,
           "reasons": ["OUTCOME_NOT_AMBIGUOUS"]},  # sorted machine codes
  "invoked": false,
  "output_used": false,
  "error": null,                                   # UNAVAILABLE|TIMEOUT|INVALID_RESPONSE|SCHEMA_VIOLATION
  "fallback_applied": null,                        # "HOLD" | "ESCALATE" — audit only (§N.2)
  "advisory": null                                 # the validated advisory object, §M.2
}
```

### E.6 `rationale`

```python
"rationale": {
  "outcome_sentence": "PROCEED: candidate 'defer_to_agent-1' is permitted and its "
                      "WEIGH score 0.75 meets proceed_min_score 0.75.",
  "reasons": ["CONSTRAINTS_RECHECKED_CLEAN", "AUTHORITY_SATISFIED",
              "SCORE_AT_OR_ABOVE_PROCEED_MIN"],
  "claude_narrative": null                         # the ONLY field advisory text may occupy
}
```

`outcome_sentence` is assembled from a fixed template over values already in the output — no model, no clock, no randomness. `claude_narrative` is `null` on every non-`AMBIGUOUS` outcome and on every advisor failure.

---

## F. The deterministic decision flow

Seven phases, executed in order. Phases 0–5 are pure; the advisor is not reachable until phase 6, by which time the outcome is already final.

```
Phase 0  PREFLIGHT   validate weigh_output, validate the policy sections GOVERN needs,
                     assert compute_policy_hash(policy) == weigh_output.policy_hash
Phase 1  RE-CHECK    re-derive every hard constraint per candidate from RAW evidence;
                     compare against WEIGH's advisory findings
Phase 2  AUTHORITY   per-agent limits + actions_requiring_governance gate
                     + actions_requiring_escalation matching (strategy AND actions)
Phase 3  PERMIT      permitted = candidates passing Phase 1 and Phase 2;
                     order by (-weigh.total_score, candidate_id)      ← no re-scoring
Phase 4  OUTCOME     the decision table below; exactly one outcome
Phase 5  AUTHORIZE   execution_authorized = (outcome == "PROCEED")
                     decision_id computed here — BEFORE any advisor exists
Phase 6  ADVISE      optional bounded Claude call; may write ONLY rationale.claude_narrative
                     + claude.* + the one documented AMBIGUOUS→ESCALATE transition (§N.2)
Phase 7  ASSEMBLE    output construction; audit-field completeness assertion
```

### F.1 The decision table (Phase 4)

Given `permitted` (ordered) and `top = permitted[0] if permitted else None`, **first match wins**:

| # | Condition | Outcome | `outcome_basis` |
|---|---|---|---|
| D1 | `permitted` is empty | `ESCALATE` | `NO_PERMITTED_CANDIDATE` |
| D2 | `weigh_agreement.agreed is False` | `ESCALATE` | `GOVERN_WEIGH_DISAGREEMENT` |
| D3 | `top.authority.requires_escalation` | `ESCALATE` | `ACTION_REQUIRES_ESCALATION` |
| D4 | `ambiguity_applies(...)` — §J.1 | `AMBIGUOUS` | `AMBIGUITY_DETECTED` |
| D5 | `case.conflict is False` | `PROCEED` | `NO_CONFLICT_ALL_CHECKS_PASSED` |
| D6a | `top.total_score >= proceed_min_score` | `PROCEED` | `SCORE_AT_OR_ABOVE_PROCEED_MIN` |
| D6b | `top.total_score <= hold_max_score` | `HOLD` | `SCORE_AT_OR_BELOW_HOLD_MAX` |
| D6c | otherwise (the mid band) | `mid_band_outcome` | `SCORE_IN_MID_BAND` |

**Why this order:**

- **D1/D2/D3 before everything.** A blocked, disputed, or escalation-flagged case is not a case whose score is worth reading.
- **D4 before D6.** An ambiguity signal is a statement that *the comparison itself is not trustworthy*. Reading a band off an untrustworthy comparison and calling it `PROCEED` is precisely the failure the ambiguity machinery exists to prevent. Consequence, accepted deliberately: a near-tie at 0.80 vs 0.78 yields `AMBIGUOUS`, not `PROCEED`. Policy's `escalation.conditions.ambiguous` is unconditioned on score, which supports this.
- **D5 before D6.** This *is* the no-conflict rule of §C.3, and it sits at position 5 — after every permission gate, not before them. `RELEASE_PAYMENT` reaches D5 only having already survived D1.
- **D6 is the only place a score is read**, and the score is WEIGH's.

`execution_authorized = (outcome == "PROCEED")`. `PROCEED` is reachable only via D5 or D6a, both of which require a non-empty `permitted` set whose top element passed every check in Phases 1–2. There is no other assignment to `execution_authorized` anywhere in the layer.

### F.2 Where each policy escalate-condition lands

`escalation.conditions.escalate` reads: *"A hard constraint is violated, agent authority is exceeded, or the case matches an authority action requiring escalation."*

| Policy clause | Row |
|---|---|
| hard constraint violated | D1 — violation ⇒ not permitted; the specific constraint appears in `blocking_reasons` |
| agent authority exceeded | D1 — same mechanism, via `HC_UNAUTHORIZED_ACTION` and §H.1 |
| matches an action requiring escalation | D3 |

---

## G. Hard-constraint re-check (Phase 1)

### G.1 What "independent" means here, precisely

GOVERN re-runs the five constraint evaluators **against raw `agent_actions` / `case_context` / `policy`**, and ignores `weigh_output.candidates[].constraint_findings` except as a value to compare against.

**Decision: GOVERN imports and re-runs `weigh.constraints.evaluate_constraints_for_candidate` rather than reimplementing the five evaluators.**

The independence that matters in this system is independence *from `weigh_output`*, not independence *from the evaluator code*. A second hand-written implementation of five predicates would be ~150 lines of duplication whose realistic failure mode — the two copies drifting apart — is worse than the failure it guards against. The threat this re-check actually defends against is a `weigh_output` that is stale, hand-edited, replayed from a different policy, or corrupted in transit, and re-running the evaluators from raw evidence catches all four.

The import direction (`govern` → `weigh`) follows the pipeline and is acceptable. *Proposed, not made:* if the evaluators ever need to be shared more widely, move them to `backend/policy/constraints.py` and have both layers import from there. That is a refactor of WEIGH code and is explicitly out of scope for this task.

### G.2 Statuses and blocking

Inherited unchanged from WEIGH §I.3:

| Status | Permitted? |
|---|---|
| `NOT_APPLICABLE` | yes |
| `SATISFIED` | yes |
| `VIOLATED` | **no** |
| `INDETERMINATE` | **no** — an unverifiable constraint is never treated as satisfied |

The `INDETERMINATE` rule is load-bearing and verified: a `NO_CONFLICT_PROCEED` release evaluated with only `payouts` and `dispute` in `agent_actions` yields `HC_THIRDWATCH_HIGH_RISK_PAYOUT: INDETERMINATE {"rto.proposed_action": null}` at **every** amount, so the release is not permitted. *A missing RTO verdict is not read as "no RTO risk."* That is one of the strongest safety statements in the demo and it costs nothing to present.

### G.3 The agreement check

```python
agrees = (govern_status == weigh_status)
```

per `(candidate_id, constraint_id)`. Any `agrees is False` populates `weigh_agreement.disagreements` and triggers D2 ⇒ `ESCALATE`. Blocked is the union of both layers' blocking sets: a candidate WEIGH blocked and GOVERN cleared is still not permitted, and vice versa.

---

## H. Authority enforcement (Phase 2)

This is the half of governance WEIGH deliberately never touched. `HC_UNAUTHORIZED_ACTION` already covers per-agent `autonomous_actions` and `max_autonomous_amount` and is re-checked in Phase 1; what follows is what Phase 2 adds on top.

### H.1 Per-agent limits — the verified boundary

From `weigh.constraints._eval_unauthorized_action`, the comparison is `amount > max_autonomous_amount` ⇒ `VIOLATED`. The cap is therefore **inclusive**: `50000` is authorized, `50001` is not. Verified end to end in §S.3.

A cap that applies with **no `amount` field on the agent's payload** is `INDETERMINATE`, not authorized. This is currently unavoidable for `retention` (cap 5 000, and `mock_agents/retention.py` publishes no `amount`) — flagged in §R.6.

There is no per-action cap and no currency field; `amount` is a bare key. Both are noted in §R.6 as accepted demo scope.

### H.2 `actions_requiring_escalation` — match strategy *and* actions

Policy: `actions_requiring_escalation: [HOLD_BOTH_PENDING_REVIEW]`. That token is a RESOLVE **strategy** (`resolve/resolver.py`), never an action — it appears in `scoring.strategy_effects`, not `scoring.action_effects`.

```python
matched = [f"action:{a}" for a in candidate.resulting_actions if a in requiring_escalation] \
        + ([f"strategy:{candidate.strategy}"] if candidate.strategy in requiring_escalation else [])
requires_escalation = bool(matched)
```

**Semantics — evaluated at selection, not at candidate-set membership.** A flagged candidate is still *permitted*: it stays in the ordered set and it can be `candidate_under_review`. What it can never be is *autonomously executed*. The case-level `ESCALATE` fires (D3) only when the flagged candidate is `permitted[0]`.

The two alternatives were considered and rejected:

- *Escalate whenever a flagged candidate exists in the set* — RESOLVE emits `hold_both_pending_review-2` for **every** resolvable conflict, so this escalates every conflict case in the product.
- *Exclude flagged candidates from the permitted set* — this deletes the conservative fallback from the comparison, which is exactly backwards.

Under the rule as written, `HOLD_BOTH_PENDING_REVIEW` can never be autonomously executed (matching the grounding finding) while remaining a live option a human can be asked about.

This also gives the unreachable-today `unresolved: true` path (RESOLVE's `hold_both_pending_review-1`, emitted when no resolution rule matches) the right behaviour for free: it is the sole candidate, it is permitted, it carries the flag, D3 fires, `ESCALATE`. *(Verified: every conflicting pair in `CONFLICT_RULES` has a matching `RESOLUTION_RULE`, so this path cannot be reached through the current tables — it needs a synthetic fixture, §U.2 #33.)*

### H.3 `actions_requiring_governance` — the governance gate with teeth

`actions_requiring_governance: [RELEASE_PAYMENT, WIN_BACK_OFFER]`. GOVERN never short-circuits permission evaluation for anyone, so this list must mean something stronger than "don't skip governance" or it is decoration.

**It means: for these actions, having run governance must be *provable in the receipt*, not merely true.**

For every candidate containing a gated action, GOVERN emits:

```python
"governance_gate": {
  "gated_actions": ["RELEASE_PAYMENT"],
  "checks_run": {
    "constraint_recheck_performed": true,
    "originating_agent_resolved": true,          # exactly one agent proposed this action
    "authority_entry_found": true,               # authority.agents[agent] exists
    "amount_limit_evaluated": true               # cap applied, or provably absent
  },
  "all_determinate": true
}
```

and applies one extra rule: **a gated action whose gate is not `all_determinate` makes the candidate not permitted**, with `blocking_reasons: ["GOVERNANCE_GATE_INDETERMINATE:RELEASE_PAYMENT"]`. In practice this is already implied by the `INDETERMINATE`-blocks rule (§G.2); the gate makes it explicit, per-action, and auditable, so a judge can be shown the exact record proving the ₹50 000 release was governed rather than waved through.

§U.2 #6 asserts: no output with `execution_authorized: true` and a gated action in `authorized_actions` may have `governance_gate: null` or `all_determinate: false`.

### H.4 Verified authority coverage gaps

Run against the real policy: three of the nine actions in `scoring.action_effects` appear in **no** agent's `autonomous_actions` and are therefore unauthorizable by any agent:

`ALLOW_ORDER`, `NO_RETENTION_ACTION`, `RETENTION_MESSAGE`

Consequence, verified: a benign no-conflict pair such as `rto: ALLOW_ORDER` + `retention: WIN_BACK_OFFER` is blocked with `HC_UNAUTHORIZED_ACTION: VIOLATED — action_not_in_autonomous_actions`. Flagged in §R.6 as a policy correction, **not made here**.

---

## I. Score bands and the mid-band gap

### I.1 The gap, verified

`escalation.thresholds` defines `proceed_min_score: 0.75` and `hold_max_score: 0.40`. **The interval `0.40 < score < 0.75` has no rule**, and it is reachable in ordinary operation:

| Verified case | Score | Band |
|---|---|---|
| payouts vs dispute, `trusted_merchant` profile | **0.6475** | undefined |
| rto vs retention, `standard` profile | **0.6300** | undefined |
| `hold_both_pending_review-2`, `standard` | **0.6200** | undefined |
| no-conflict release + close, `standard` | 0.3100 | HOLD band |
| payouts vs dispute, `standard` | 0.7500 | PROCEED band (exactly at the boundary) |

Three of the five verified scores in this system land in the undefined band.

### I.2 The rule: GOVERN reads the band from policy, and refuses to guess

Hard-coding "mid band means HOLD" in GOVERN would put a governance threshold in application code, which the whole architecture exists to avoid. Inventing a third threshold is worse.

**GOVERN reads `escalation.thresholds.mid_band_outcome` and raises `GovernPolicyError` at preflight if it is absent.** Policy gaps raise; evidence gaps are reported — the same rule WEIGH follows (§N.1 there).

This is deliberate and slightly aggressive: until the one-line policy change in §R.1 is applied, GOVERN fails preflight on *every* case, including cases that would never touch the mid band. That is the point — a missing band definition is not the kind of thing that should surface for the first time on stage, in the one case that happens to score 0.6475.

### I.3 Band boundaries

```
score >= proceed_min_score   →  PROCEED_BAND     # inclusive: 0.7500 proceeds
score <= hold_max_score      →  HOLD_BAND        # inclusive: 0.4000 holds
otherwise                    →  MID_BAND         → mid_band_outcome
```

Both boundaries inclusive, matching WEIGH's inclusive near-tie convention (§J.1 there) and `HC_CONFIDENCE_FLOOR`'s inclusive floor (verified: 0.60 satisfies, 0.59 violates). One convention, applied everywhere.

### I.4 The band is evaluated on the top **permitted** candidate

Not on `ranking[0]`, not on the highest raw score. WEIGH's `ranking` already sorts eligible-first, so the two usually coincide — but GOVERN's permitted set is its own (the union of both layers' blocking, plus the authority gates WEIGH never ran), so it must read the score of the candidate *it* would authorize. A blocked candidate's score never reaches the band comparison.

---

## J. Ambiguity handling

GOVERN **reads** `weigh_output.ambiguity` and never recomputes it — ambiguity is a property of the comparison, and the comparison is WEIGH's.

### J.1 `ambiguity_applies`

```python
codes           = {s["code"] for s in weigh_output["ambiguity"]["signals"]}
comparative     = codes & {"NEAR_TIE", "CONFLICTING_OBJECTIVES"}
non_comparative = codes & {"LOW_CONFIDENCE", "INSUFFICIENT_EVIDENCE"}

applies = weigh_output["ambiguity"]["detected"] and (
    (bool(comparative) and len(permitted) >= 2) or bool(non_comparative)
)
```

The `len(permitted) >= 2` guard on comparative signals is the one refinement GOVERN adds. WEIGH detects a near-tie across its *eligible* set; if GOVERN's authority gates then permit only one of the tied pair, the tie is moot and reporting `AMBIGUOUS` over a field of one would be misleading. Non-comparative signals (weak or incomplete evidence) are about the case, not the comparison, so they apply regardless of how many candidates survive.

`ALL_CANDIDATES_CONSTRAINED` never reaches this function — D1 catches an empty permitted set first. `SINGLE_CANDIDATE` is informational and does not set `detected` (verified in `weigh/ambiguity.py`).

### J.2 `AMBIGUOUS` never authorizes execution

`execution_authorized` is `false` for `AMBIGUOUS` by the single derivation in §F.1. This is what makes the Claude gate safe: the *only* outcome on which Claude may be consulted is one that has already been decided not to execute.

---

## K. Escalation behaviour

`ESCALATE` means: **no autonomous execution, route to a human, and say precisely why.** GOVERN emits `escalation.reasons` as sorted, stable machine codes so the receipt and the UI can render them without parsing prose:

| Code | Emitted when |
|---|---|
| `NO_PERMITTED_CANDIDATE` | D1 |
| `HC_<ID>:VIOLATED` | that constraint blocked a candidate in Phase 1 |
| `HC_<ID>:INDETERMINATE` | evidence for that constraint was missing |
| `GOVERNANCE_GATE_INDETERMINATE:<ACTION>` | §H.3 |
| `AUTHORITY_EXCEEDED:<AGENT>:<ACTION>` | per-agent cap or action list |
| `ACTION_REQUIRES_ESCALATION:<match>` | D3, e.g. `strategy:HOLD_BOTH_PENDING_REVIEW` |
| `GOVERN_WEIGH_DISAGREEMENT:<candidate>:<constraint>` | D2 |
| `CLAUDE_SCHEMA_VIOLATION` | §N.2 |

`escalation.required` mirrors `outcome == "ESCALATE"`; it exists because receipts read better with an explicit boolean than with a string comparison.

---

## L. The Claude gate

### L.1 Claude is a port, not a dependency

`backend/govern/` **must not import `anthropic`**, an HTTP client, or any SDK. The advisor arrives as an injected object satisfying a tiny Protocol:

```python
# backend/govern/advisor.py
from typing import Optional, Protocol

class Advisor(Protocol):
    def explain(self, request: dict) -> Optional[dict]:
        """Return an advisory dict, or None if unavailable. Should not raise;
        if it does, GOVERN treats it as UNAVAILABLE. Owns its own timeout."""

class NullAdvisor:
    def explain(self, request: dict) -> None:
        return None
```

`advisor=None` ⇒ `NullAdvisor()`. The default path through GOVERN therefore involves no model at all, and an `ast`-based import test (mirroring `weigh/test_open_track_safety.py::test_no_forbidden_imports_in_weigh_source`) proves it structurally rather than by convention.

A real Anthropic-backed adapter, if the team wants one for the demo, lives **outside** the package — `backend/advisors/claude_advisor.py` — and is wired by the orchestrator. It is not part of this design and is not required for any invariant in §U.

*(There is no `anthropic` entry in the project's dependencies today. Nothing in this design adds one.)*

### L.2 The gate

Claude is invoked **only** when all four conditions hold. All four are recorded in `claude.gate`:

| # | Condition | Source |
|---|---|---|
| 1 | `outcome == "AMBIGUOUS"` | `policy.claude.invocation_conditions[0]` |
| 2 | no `VIOLATED` **and** no `INDETERMINATE` in any candidate's Phase-1 re-check | `invocation_conditions[1]`, tightened to include `INDETERMINATE` |
| 3 | `execution_authorized is False` | structural guard — makes Claude parity true *by construction* |
| 4 | an advisor was injected (not `NullAdvisor`) | — |

Condition 3 is redundant with condition 1 today (D4 always yields `AMBIGUOUS`, which is never authorized). It is asserted anyway, because it is the invariant that must survive any future change to the decision table: **an advisor can never be reached on a path that authorizes execution.** If a later edit ever made `AMBIGUOUS` authorizable, condition 3 shuts the advisor off rather than letting it participate in an authorized decision.

Before invoking, GOVERN asserts the four policy invariants are still `false` — `may_invent_candidates`, `may_bypass_hard_constraints`, `may_override_authority`, `may_directly_execute_actions` — and raises `GovernPolicyError` if any is not. `policy.loader._validate_claude` already enforces this at load time; GOVERN re-asserts at the call site, where it matters.

### L.3 What Claude receives

A **built, redacted** request — never `agent_actions`, never `case_context`, never the policy dict:

```python
{
  "advisory_request_version": "1.0.0",
  "question": "explain_ambiguity",
  "case": {"entity_type": …, "conflict": true},           # no case_id, no merchant_id
  "profile": "standard",
  "ambiguity_signals": [ … ],                              # codes + details from WEIGH
  "candidates": [                                          # PERMITTED candidates only
    {"candidate_id": …, "strategy": …, "resulting_actions": [ … ],
     "total_score": 0.6300,
     "objective_contributions": {"financial_exposure_prevention": 0.2850, … }}
  ],
  "constraint_summary": [{"constraint_id": …, "status": "SATISFIED"}]
}
```

Built from an explicit `ADVISOR_REQUEST_FIELDS` whitelist, so adding a field to any upstream payload cannot silently widen what leaves the process. Amounts, merchant identifiers, dispute ids, and raw agent payloads are excluded — an explanation of *why two governance options are close* does not need them.

### L.4 What Claude can and cannot touch

| May write | May never write |
|---|---|
| `rationale.claude_narrative` | `outcome` (except the one transition in §N.2, which GOVERN performs, not Claude) |
| `claude.advisory` | `execution_authorized` |
| `claude.invoked` / `output_used` / `error` | `selected_candidate`, `authorized_actions` |
| — | `permission_evaluation.*`, `permitted_candidate_ids` |
| — | `score_band.*`, any score, `decision_id` |

Enforced three ways, not one: (a) the response validator's key allowlist and denylist (§M.3); (b) the assembly order — `decision_id` and `execution_authorized` are computed in Phase 5, before the advisor exists in Phase 6; (c) the parity tests in §U.

---

## M. The Claude response contract

### M.1 Design constraint

Small, flat, and boring. Every additional field is another thing to validate and another way for a model to say something the receipt then has to defend.

### M.2 Schema

```python
{
  "advisory_version": "1.0.0",                  # required, must equal ADVISORY_VERSION
  "summary": "<plain text, 1..500 chars>",      # required
  "key_tradeoffs": ["<1..200 chars>", …],       # required, 0..5 items
  "suggested_candidate_id": "defer_to_agent-1" | null,   # required key, nullable
  "confidence_note": "<1..200 chars>" | null    # required key, nullable
}
```

### M.3 Validation — deterministic, in GOVERN, no model involved

1. Top level is a `dict` whose key set is **exactly** the five above. Any missing or extra key ⇒ `SCHEMA_VIOLATION`.
2. `advisory_version` equals the constant, else `INVALID_RESPONSE`.
3. Types and length bounds as stated, else `INVALID_RESPONSE`.
4. `suggested_candidate_id` is `null` or a member of `permitted_candidate_ids`. **Any other value — including a valid-looking id GOVERN did not permit, or a new id — is `SCHEMA_VIOLATION`**, because it is an attempt to introduce a candidate.
5. Recursive denylist walk. Any key matching `{outcome, decision, execution_authorized, authorized, approve, approved, override, bypass, escalate, execute, action, actions, new_candidate, candidate, policy, authority, constraint}` at any depth ⇒ `SCHEMA_VIOLATION`.
6. All strings are treated as **inert text**. Never `eval`'d, never parsed as JSON, never used as a dict key, never used to look anything up. They are copied into `rationale.claude_narrative` and nowhere else.

Any failure discards the advisory **whole** — no partial acceptance, no field-level salvage. `claude.output_used` stays `false` and `claude.advisory` stays `null`.

`suggested_candidate_id` survives validation as **non-binding narrative**: on an `AMBIGUOUS` case a human is reviewing anyway, "of the two permitted options 0.01 apart, the advisor points at the hold, because …" is genuinely useful and costs nothing, because the outcome is already `AMBIGUOUS` and `execution_authorized` is already `false`. §U.2 #22 pins that.

---

## N. Fallback behaviour

### N.1 The vocabulary bridge

`fallback.*` values are `HOLD_FOR_REVIEW` / `ESCALATE`; `escalation.outcomes` are `PROCEED / HOLD / ESCALATE / AMBIGUOUS`. `HOLD_FOR_REVIEW` is not an outcome and must never be assigned to `outcome`.

```python
# backend/govern/schema.py
FALLBACK_OUTCOME_ALIASES = {
    "HOLD_FOR_REVIEW": "HOLD",
    "HOLD":            "HOLD",
    "ESCALATE":        "ESCALATE",
}
```

Three lines. Correct against the policy as it stands today **and** against the corrected vocabulary proposed in §R.2, so the implementation is not blocked on that decision. Any fallback value not in the map ⇒ `GovernPolicyError` at preflight.

### N.2 Fallback never weakens, and almost never changes, the outcome

The governance outcome is final at the end of Phase 5, **before** the advisor is reachable. An advisor that is missing, slow, broken, or malicious therefore cannot change what governance already decided. `fallback.on_claude_unavailable: HOLD_FOR_REVIEW` is already satisfied by the outcome being `AMBIGUOUS` — which, like `HOLD`, authorizes nothing.

**Exactly one post-advisor outcome transition is permitted:**

```
AMBIGUOUS  →  ESCALATE     iff  claude.error == "SCHEMA_VIOLATION"
```

driven by `fallback.on_schema_violation: ESCALATE`. It fires when the advisor tried to name an outcome, override a constraint, or introduce a candidate. A human should see that, and `ESCALATE` is how GOVERN says so. It moves strictly *toward* caution and cannot produce `PROCEED`, so `execution_authorized` is `false` on both sides of the arrow and Claude parity holds.

Every other advisor failure — `UNAVAILABLE`, `TIMEOUT`, `INVALID_RESPONSE` — leaves `outcome` untouched, sets `claude.error`, records `claude.fallback_applied` for audit, and sets `output_used: false`.

| Advisor state | `claude.error` | `fallback_applied` | Outcome | `execution_authorized` |
|---|---|---|---|---|
| absent (`NullAdvisor`) | `null` | `null` | `AMBIGUOUS` | `false` |
| returns valid advisory | `null` | `null` | `AMBIGUOUS` | `false` |
| returns `None` / raises | `UNAVAILABLE` | `HOLD` | `AMBIGUOUS` | `false` |
| times out (port-owned) | `TIMEOUT` | `HOLD` | `AMBIGUOUS` | `false` |
| malformed values | `INVALID_RESPONSE` | `HOLD` | `AMBIGUOUS` | `false` |
| forbidden key / unpermitted id | `SCHEMA_VIOLATION` | `ESCALATE` | **`ESCALATE`** | `false` |

The last column is constant. That column *is* constraint 4 of this task, and §U.2 #17–21 assert it row by row.

### N.3 Timeouts belong to the port

GOVERN never sleeps, never retries, never sets a deadline. The injected adapter owns its timeout and returns `None` (or raises) when it expires. GOVERN stays free of clocks, which is what keeps §P.1 true.

---

## O. Audit and receipt fields

`policy.audit.required_fields` has fifteen entries. GOVERN supplies fourteen; the orchestrator supplies one.

| Required field | Source |
|---|---|
| `policy_id` | GOVERN top level (echoed from `weigh_output`) |
| `policy_version` | GOVERN top level |
| `policy_hash` | GOVERN top level (re-verified against the policy dict in Phase 0) |
| `decision_id` | GOVERN, §P.2 |
| `timestamp` | **Orchestrator.** GOVERN emits none (§P.1) |
| `profile_selected` | GOVERN `profile_selected` ← `weigh_output.profile.profile_name` |
| `objectives_considered` | GOVERN, sorted keys of any `objective_impacts` |
| `weights_used` | GOVERN, echoed from `weigh_output.profile.weights` |
| `hard_constraints_checked` | GOVERN `permission_evaluation.constraints_checked` |
| `candidates_considered` | GOVERN `permission_evaluation.candidates[].candidate_id` |
| `selected_candidate` | GOVERN `selected_candidate` (null unless `PROCEED`) |
| `outcome` | GOVERN `outcome` |
| `rationale` | GOVERN `rationale` |
| `claude_invoked` | GOVERN `claude.invoked` |
| `claude_output_used` | GOVERN `claude.output_used` |

Phase 7 asserts this mapping is total: every entry in `policy.audit.required_fields` other than `timestamp` resolves to a non-missing path in the output, else `GovernPolicyError`. A future policy edit that adds a required field then fails loudly instead of producing a quietly incomplete receipt (§U.2 #26).

The Decision Receipt itself — assembly, persistence, rendering — is **out of scope**, exactly as it was for WEIGH.

---

## P. Determinism

### P.1 Purity contract

**Same five inputs ⇒ byte-identical output**, where the fifth (the advisor) is either absent or itself deterministic.

| Requirement | Rule |
|---|---|
| No clock | No `datetime`, `time`, or timestamp field anywhere in `backend/govern/`. `timestamp` is the orchestrator's |
| No randomness | No `random`, no `uuid`. `decision_id` is a content hash |
| No I/O | No `open`, no DB, no network, no `load_policy`. Policy arrives as an argument |
| No SDK | No `anthropic`, `requests`, `httpx`, `urllib`, `socket`, `subprocess` — `ast`-verified |
| No global state | No module-level mutable caches, no `os.environ` |
| Stable ordering | All emitted lists sorted or explicitly ordered; sets never emitted |
| No new numbers | GOVERN performs comparisons, not arithmetic. Scores are copied |
| No mutation | The four inputs are never mutated (deepcopy-compared in tests) |
| No dynamic execution | No `eval` / `exec`; no `getattr` dispatch on policy or advisory strings |

### P.2 `decision_id`

```python
payload = {
    "govern_version": GOVERN_VERSION,
    "policy_hash":    weigh_output["policy_hash"],
    "case_context":   case_context,
    "weigh_output":   weigh_output,
}
digest = hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
).hexdigest()
decision_id = f"dec_{digest}"
```

- **Computed in Phase 5, before the advisor exists.** Advisory content is therefore structurally excluded, which is why `decision_id` is identical with and without Claude (§U.2 #20).
- `case_context` is included because `weigh_output` does not carry the amount: the ₹10 000 and ₹50 000 releases produce *identical* `weigh_output` (both `SATISFIED`, same score, same findings) and would otherwise collide. `case_id` in `case_context` separates them in practice.
- It is a **content fingerprint, not a unique event id**. Re-running the same case yields the same id — the desirable property for a receipt. The orchestrator pairs it with `timestamp` when per-run uniqueness is needed.

---

## Q. Errors

Same rule as WEIGH: **policy gaps raise, evidence gaps are reported.**

`GovernInputError` — integration is broken:
- `weigh_output` missing a required key, or malformed
- `compute_policy_hash(policy) != weigh_output.policy_hash`
- `constraint_evaluation.authority != "advisory_only"` or `rechecked_by != "GOVERN"`
- a forbidden WEIGH key present at any depth
- a `preferred_agent`, `agent_a`, or `agent_b` absent from `agent_actions`

`GovernPolicyError` — governance is misconfigured:
- `escalation.thresholds.mid_band_outcome` missing, or not in `{HOLD, ESCALATE}` (§R.1)
- `escalation.outcomes` missing any of `PROCEED / HOLD / ESCALATE / AMBIGUOUS`
- a `fallback.*` value not in `FALLBACK_OUTCOME_ALIASES`
- any `claude.may_*` invariant not `false`
- a `hard_constraints[].id` with no registered evaluator
- an `audit.required_fields` entry (other than `timestamp`) GOVERN cannot supply

Reported, never raised: missing evidence (`INDETERMINATE` findings), advisor failures, unresolvable originating agents. All become blocking reasons or `notes`, never exceptions — an unavailable model must never take the governance layer down.

**GOVERN never emits a partial output.** All preflight checks run before Phase 1.

---

## R. Policy corrections — proposed, NOT made

None of the following has been applied. `policy_bundle.yaml`, `policy_schema.json`, `loader.py`, and every test are untouched by this task.

### R.1 Required — the mid-band gap

**Problem (verified):** `0.40 < score < 0.75` has no rule, and 0.6475 / 0.6300 / 0.6200 all land there in real cases.

```yaml
escalation:
  thresholds:
    proceed_min_score: 0.75
    hold_max_score: 0.40
    mid_band_outcome: HOLD     # NEW — covers hold_max_score < score < proceed_min_score
```

Also: add `mid_band_outcome` to `policy_schema.json` under `escalation.thresholds`, and add a `loader` check that its value ∈ `{HOLD, ESCALATE}`. `PROCEED` must be rejected — an undefined band may never auto-execute. `AMBIGUOUS` is excluded too: ambiguity is derived from ambiguity signals, and letting a score band also name it would give one outcome two unrelated sources.

**Blocking.** GOVERN raises `GovernPolicyError` at preflight without it (§I.2).

### R.2 Recommended — the fallback vocabulary mismatch

**Problem (verified):** `fallback.*` uses `HOLD_FOR_REVIEW`, which is absent from `escalation.outcomes`.

```yaml
fallback:
  on_claude_unavailable: HOLD      # was HOLD_FOR_REVIEW
  on_invalid_response:   HOLD      # was HOLD_FOR_REVIEW
  on_timeout:            HOLD      # was HOLD_FOR_REVIEW
  on_schema_violation:   ESCALATE  # unchanged
```

Requires updating `loader.CONSERVATIVE_FALLBACK_ACTIONS` to `{"HOLD", "ESCALATE"}` and any loader test asserting the old tokens.

**Not blocking.** `FALLBACK_OUTCOME_ALIASES` (§N.1) accepts both spellings, so GOVERN is correct before and after.

### R.3 Recommended — strategy vs action in `actions_requiring_escalation`

**Problem (verified):** `HOLD_BOTH_PENDING_REVIEW` is a RESOLVE strategy sitting in an action-named field.

```yaml
authority:
  actions_requiring_escalation: []                          # now genuinely actions
  strategies_requiring_escalation:                          # NEW
    - HOLD_BOTH_PENDING_REVIEW
```

Plus `strategies_requiring_escalation` in the schema (optional array of strings).

**Not blocking.** §H.2 matches strategy tokens in *either* field, so GOVERN behaves identically before and after.

### R.4 Optional — make `claude.invocation_conditions` machine-readable

**Problem (verified):** it is a list of English sentences. `loader` validates it is a list of strings; nothing can execute it. GOVERN's gate (§L.2) is therefore hard-coded to match the prose.

```yaml
claude:
  gate:                                        # NEW, machine-readable
    required_outcome: AMBIGUOUS
    forbid_when_constraint_status_in: [VIOLATED, INDETERMINATE]
    require_execution_unauthorized: true
  invocation_conditions: [ … ]                 # kept as human documentation
```

**Not blocking.** The prose and the coded gate agree today; §U.2 #16 pins the coded gate so a future divergence is caught.

### R.5 Informational — threshold layering

`ambiguity.low_confidence_threshold: 0.55` sits **below** `HC_CONFIDENCE_FLOOR.parameters.min_confidence: 0.60`, so the hard floor always bites first for any acting candidate. Not a bug — they have different scopes (`case_confidence` across contributing agents vs the *originating* agent's own confidence) and different jobs (a signal vs a block). Worth one clarifying YAML comment so a reader does not "fix" the ordering. No code change.

### R.6 Informational — authority coverage gaps found during inspection

| Finding (verified) | Effect today |
|---|---|
| `ALLOW_ORDER`, `NO_RETENTION_ACTION`, `RETENTION_MESSAGE` appear in no agent's `autonomous_actions` | any candidate containing one is `HC_UNAUTHORIZED_ACTION: VIOLATED` and never permitted |
| `retention.max_autonomous_amount: 5000`, but `mock_agents/retention.py` publishes no `amount` | `WIN_BACK_OFFER` is permanently `INDETERMINATE` ⇒ never autonomously authorizable |
| No per-action cap; only per-agent | `RELEASE_PAYMENT` inherits `payouts`' ₹50 000 for every release |
| No currency field; `amount` is a bare key | acceptable demo scope; worth one sentence in the disclaimer |

All four are safe-by-default (they block rather than permit), so none is urgent. Listed so the team decides deliberately rather than discovering them mid-demo.

---

## S. Worked examples — verified against the real code

All three were produced by running `conflict_matrix` → `resolve` → `weigh` at `985d430`. WEIGH's numbers are quoted exactly; GOVERN's columns follow the decision table in §F.1. All three assume §R.1 has been applied with `mid_band_outcome: HOLD`.

### S.1 — `0.7500`, exactly at `proceed_min_score`

```python
payouts = {"agent": "payouts", "proposed_action": "RELEASE_PAYMENT",
           "confidence": 0.95, "amount": 42000, "days_overdue": 9}
dispute = {"agent": "dispute", "proposed_action": "HOLD_RELATED_ACTIONS",
           "confidence": 0.95, "dispute_status": "OPEN", "disputed_amount": 42000}
case_context = {"case_id": "case-Q", "merchant_id": "mrch_001"}    # ⇒ standard profile
entity_type  = "order_vendor"
```

**WEIGH (verified):**

| Candidate | strategy | actions | `total_score` | eligible |
|---|---|---|---|---|
| `defer_to_agent-1` | `DEFER_TO_AGENT` (pref. `dispute`) | `["HOLD_RELATED_ACTIONS"]` | **0.7500** | true |
| `hold_both_pending_review-2` | `HOLD_BOTH_PENDING_REVIEW` | `[]` | 0.6200 | true |

`case_confidence 0.9500`; `top_gap 0.1300`; `ambiguity.detected: false`; `signals: []`.

**GOVERN:**

| Phase | Result |
|---|---|
| 1 re-check | `defer_to_agent-1`: `HC_CONFIDENCE_FLOOR SATISFIED (0.95 ≥ 0.60)`, `HC_UNAUTHORIZED_ACTION SATISFIED (dispute, no_amount_limit)`, other three `NOT_APPLICABLE`. `hold_both-2`: all five `NOT_APPLICABLE` (no actions). Agreement: full |
| 2 authority | `defer_to_agent-1`: no gated action, `requires_escalation false`. `hold_both-2`: `strategy:HOLD_BOTH_PENDING_REVIEW` matched ⇒ `requires_escalation true` |
| 3 permit | both permitted; ordered `[defer_to_agent-1 (0.7500), hold_both_pending_review-2 (0.6200)]` |
| 4 outcome | D1 no · D2 no · D3 top not flagged · D4 `detected false` · D5 `conflict true` · **D6a `0.7500 >= 0.75`** ⇒ **`PROCEED`** |
| 5 authorize | `execution_authorized: true`; `selected_candidate: defer_to_agent-1`; `authorized_actions: ["HOLD_RELATED_ACTIONS"]` |
| 6 advise | gate ineligible (`OUTCOME_NOT_AMBIGUOUS`, `EXECUTION_AUTHORIZED`) ⇒ not invoked |

**Boundary behaviour, three verified variants of the same case:**

| Variant | Score | Band | Outcome |
|---|---|---|---|
| `standard` profile | **0.7500** | `PROCEED_BAND` (inclusive `>=`) | `PROCEED` |
| `high_risk_merchant` (`merchant_risk_tier: "high"`) | 0.8000 | `PROCEED_BAND` | `PROCEED` |
| `trusted_merchant` (`merchant_trust_tier: "trusted"`) | **0.6475** | **`MID_BAND`** | `HOLD` (via `mid_band_outcome`) |

The third row is the mid-band gap of §R.1 appearing in an ordinary case, and the reason GOVERN refuses to run without the policy field.

### S.2 — `0.6300` vs `0.6200`: near-tie, and the Claude case

```python
rto       = {"agent": "rto", "proposed_action": "HOLD_ORDER",
             "confidence": 0.95, "rto_score": 0.82, "shipment_status": "IN_TRANSIT"}
retention = {"agent": "retention", "proposed_action": "WIN_BACK_OFFER",
             "confidence": 0.95, "churn_risk": 0.80, "customer_value_score": 0.9}
case_context = {"case_id": "case-R"}                # ⇒ standard profile
entity_type  = "customer"
```

**WEIGH (verified):** `rto` outranks `retention`, so the deferred action is `HOLD_ORDER`.

| Candidate | actions | `total_score` | eligible |
|---|---|---|---|
| `defer_to_agent-1` | `["HOLD_ORDER"]` | **0.6300** | true |
| `hold_both_pending_review-2` | `[]` | **0.6200** | true |

`top_gap 0.0100 ≤ near_tie_threshold 0.05`; `detected: true`; signals:

```
NEAR_TIE               {top_gap 0.0100, threshold 0.05,
                        members [defer_to_agent-1, hold_both_pending_review-2]}
CONFLICTING_OBJECTIVES {favoring_top  [financial_exposure_prevention, fraud_risk_reduction,
                                       operational_cost],
                        favoring_next [compliance_risk_reduction, merchant_trust]}
```

**GOVERN:**

| Phase | Result |
|---|---|
| 1 re-check | `defer_to_agent-1`: `HC_CONFIDENCE_FLOOR SATISFIED`, `HC_UNAUTHORIZED_ACTION SATISFIED (rto, HOLD_ORDER, no_amount_limit)`. `HC_RETENTION_TO_FLAGGED_MERCHANT NOT_APPLICABLE` — `WIN_BACK_OFFER` is in no candidate's actions. Full agreement |
| 2 authority | `hold_both-2` flagged; `defer_to_agent-1` clean |
| 3 permit | both permitted; `[defer_to_agent-1 (0.6300), hold_both_pending_review-2 (0.6200)]` |
| 4 outcome | D3 top not flagged · **D4:** `detected true`, comparative signals present, `len(permitted) == 2` ⇒ **`AMBIGUOUS`** |
| 5 authorize | `execution_authorized: false`; `selected_candidate: null`; `candidate_under_review: defer_to_agent-1` |
| 6 advise | gate **eligible**: `AMBIGUOUS` ✓, no `VIOLATED` / `INDETERMINATE` ✓, unauthorized ✓, advisor injected ✓ ⇒ invoked |

Note what would have happened without D4: `0.6300` is mid-band ⇒ `HOLD`. Both outcomes refuse execution; `AMBIGUOUS` is the more informative one, and it is the case Claude exists for.

**Claude parity (constraint 4) — the same case, five advisor states:**

| Advisor | `outcome` | `execution_authorized` | `decision_id` | `claude.output_used` |
|---|---|---|---|---|
| none (`NullAdvisor`) | `AMBIGUOUS` | **false** | `dec_X` | false |
| valid advisory | `AMBIGUOUS` | **false** | `dec_X` | true |
| raises / returns `None` | `AMBIGUOUS` | **false** | `dec_X` | false |
| times out | `AMBIGUOUS` | **false** | `dec_X` | false |
| returns `{"outcome": "PROCEED", …}` | **`ESCALATE`** | **false** | `dec_X` | false |

`execution_authorized` and `decision_id` are constant down the columns. The last row is the single permitted transition (§N.2), and it moves toward caution.

### S.3 — `50000` / `50001`: the authority boundary, and why no-conflict is not a bypass

```python
payouts = {"agent": "payouts", "proposed_action": "RELEASE_PAYMENT",
           "confidence": 0.95, "amount": <varies>, "days_overdue": 9}
dispute = {"agent": "dispute", "proposed_action": "CLOSE_CASE",
           "confidence": 0.90, "dispute_status": "CLOSED", "disputed_amount": 0}
entity_type = "order_vendor"     # RELEASE_PAYMENT × CLOSE_CASE ⇒ conflict: false
```

RESOLVE emits one candidate: `no_conflict_proceed-1`, `NO_CONFLICT_PROCEED`, actions `["RELEASE_PAYMENT", "CLOSE_CASE"]`. WEIGH scores it **0.3100** (`case_confidence 0.9125`) at **every** amount — the score never moves, because the element-wise minimum over the two action vectors does not depend on the amount.

**Variant A — `agent_actions` also carries an RTO verdict** (`rto: ALLOW_ORDER`, conf 0.90):

| `amount` | WEIGH `HC_UNAUTHORIZED_ACTION` | eligible | GOVERN outcome | `execution_authorized` |
|---|---|---|---|---|
| 10 000 | `SATISFIED (within_amount_limit)` | true | **`PROCEED`** (D5) | **true** |
| **50 000** | `SATISFIED (within_amount_limit)` | true | **`PROCEED`** (D5) | **true** |
| **50 001** | `VIOLATED (amount_exceeds_max_autonomous_amount)` | false | **`ESCALATE`** (D1) | **false** |
| 60 000 | `VIOLATED` | false | **`ESCALATE`** (D1) | **false** |

The cap is inclusive: `amount > max_autonomous_amount` is the violation test, so ₹50 000 is authorized and ₹50 001 is not.

**Variant B — only `payouts` and `dispute` in `agent_actions`** (no RTO payload at all):

| `amount` | `HC_THIRDWATCH_HIGH_RISK_PAYOUT` | eligible | GOVERN outcome |
|---|---|---|---|
| 10 000 / 50 000 / 50 001 / 60 000 | `INDETERMINATE {"rto.proposed_action": null}` | false | **`ESCALATE`** (D1) at every amount |

**What this example proves, and it is the whole point of §C.3:**

1. `0.3100 ≤ hold_max_score (0.40)` in **every single row above.** If GOVERN read the band on a no-conflict case, all eight rows would be `HOLD` — including two perfectly safe releases.
2. `PROCEED` at ₹50 000 and `ESCALATE` at ₹50 001 differ by one rupee and **zero score points.** The decision came from authority, not from the band. Skipping the band did not skip governance.
3. `RELEASE_PAYMENT` is in `actions_requiring_governance`, so both `PROCEED` rows carry a `governance_gate` record with all four checks determinate. A judge can be shown the receipt line proving the release was governed.
4. Variant B is the safety story: with no RTO verdict in evidence, the release is `ESCALATE` at ₹10 000. **Missing evidence is not read as absence of risk.**

### S.4 — Boundary summary

| Boundary | Value | Behaviour | Verified via |
|---|---|---|---|
| `proceed_min_score` | 0.7500 | inclusive ⇒ `PROCEED` | §S.1 |
| just below | 0.7499 | `MID_BAND` ⇒ `mid_band_outcome` | fixture (§U.2 #9) |
| mid band, real cases | 0.6475 / 0.6300 / 0.6200 | `MID_BAND` | §S.1, §S.2 |
| `hold_max_score` | 0.4000 | inclusive ⇒ `HOLD` | fixture (§U.2 #10) |
| `max_autonomous_amount` | 50 000 / 50 001 | inclusive cap | §S.3 |
| `HC_CONFIDENCE_FLOOR` | 0.60 / 0.59 | inclusive floor (0.59 ⇒ `VIOLATED`) | verified in `weigh` |
| `near_tie_threshold` | 0.0100 ≤ 0.05 | inclusive ⇒ `NEAR_TIE` | §S.2 |

---

## T. Open Track boundary — GOVERN's part

WEIGH's §T argument (Sentinel governs *inter-agent disagreement*; it does not score entities) carries into GOVERN unchanged, plus two GOVERN-specific statements:

- **GOVERN reads no evidence magnitude into any decision.** Its inputs are booleans (constraint statuses, authority membership, list membership), a copied score it does not compute, and policy thresholds. `rto_score`, `churn_risk`, `disputed_amount`, `days_overdue` are never read. `amount` is read **only** inside `HC_UNAUTHORIZED_ACTION` as `amount > cap` — a boolean comparison against a policy number, not a risk quantity.
- **Claude cannot expand the option space.** The candidate set is closed by RESOLVE, filtered by GOVERN, and only then shown to a model — and the model's one structured field is validated against `permitted_candidate_ids`. There is no point in the pipeline at which a model can add an option, and `may_invent_candidates: false` is re-asserted at the call site.

The demo sentence: *"Sentinel's governance decision is a deterministic function of policy. Claude explains it. Turn Claude off, and the same action executes for the same reason."* §S.2's parity table is the evidence for that sentence.

---

## U. Invariants and required tests

Colocated `test_*.py` under `backend/govern/`, literal fixture dicts, no DB, no network, no clock, no randomness. Policy variants via `copy.deepcopy(load_policy())` mutated in memory, matching `weigh/test_policy_sensitivity.py`.

### U.1 Structural invariants (must hold for every input)

1. `outcome ∈ policy.escalation.outcomes` — always.
2. `execution_authorized is True` ⟺ `outcome == "PROCEED"` — no exceptions.
3. `execution_authorized is True` ⇒ `selected_candidate is not None` and it is in `permitted_candidate_ids`.
4. `execution_authorized is False` ⇒ `authorized_actions == []`.
5. `selected_candidate is None` for every non-`PROCEED` outcome.
6. Candidate id set equals `weigh_output`'s, which equals RESOLVE's.
7. No score, rank, or gap in the output that is not present verbatim in `weigh_output`.
8. `execution_authorized` and `decision_id` are invariant across all five advisor states.
9. No candidate with a `VIOLATED` or `INDETERMINATE` re-check is ever in `permitted_candidate_ids`.
10. The advisor is never invoked when `execution_authorized` is `True`.

### U.2 Test matrix

| # | Test | Asserts |
|---|---|---|
| 1 | `test_proceed_at_exact_threshold` | §S.1: `0.7500 >= 0.75` ⇒ `PROCEED`, authorized, `authorized_actions == ["HOLD_RELATED_ACTIONS"]` |
| 2 | `test_no_conflict_release_within_cap_proceeds` | §S.3 A @50 000 ⇒ `PROCEED`, `score_band.evaluated is False`, `reason_not_evaluated == "no_conflict_single_candidate"` |
| 3 | `test_no_conflict_release_over_cap_escalates` | §S.3 A @50 001 ⇒ `ESCALATE`, unauthorized, `AUTHORITY_EXCEEDED:payouts:RELEASE_PAYMENT` in reasons |
| 4 | `test_no_conflict_does_not_bypass_constraints` | §S.3 B: no RTO payload ⇒ `HC_THIRDWATCH INDETERMINATE` ⇒ `ESCALATE` @10 000 (**constraint 1**) |
| 5 | `test_no_conflict_skips_band_only` | 0.3100 ≤ `hold_max_score` yet `PROCEED`; `score_band.band is None`; every constraint and authority check present in the record |
| 6 | `test_governance_gate_recorded_for_gated_actions` | any `PROCEED` whose `authorized_actions` contains an `actions_requiring_governance` member has `governance_gate.all_determinate is True` (§H.3) |
| 7 | `test_govern_does_not_rescore` | recursive walk: every number in the output is in `weigh_output` or is a policy threshold (**constraint 2**) |
| 8 | `test_ordering_uses_weigh_total_score` | permuting `weigh_output.candidates` order leaves `permitted_candidate_ids` unchanged; `ordering_source == "weigh.total_score"` |
| 9 | `test_mid_band_uses_policy_outcome` | 0.7499 ⇒ `MID_BAND` ⇒ `mid_band_outcome`; flip the policy value to `ESCALATE` ⇒ outcome flips, code unchanged |
| 10 | `test_band_boundaries_inclusive` | 0.7500 ⇒ `PROCEED`; 0.4000 ⇒ `HOLD` |
| 11 | `test_missing_mid_band_outcome_raises` | field deleted ⇒ `GovernPolicyError` at preflight, no partial output (§R.1) |
| 12 | `test_near_tie_is_ambiguous` | §S.2: 0.6300 / 0.6200 ⇒ `AMBIGUOUS`, unauthorized, `candidate_under_review` set |
| 13 | `test_ambiguity_requires_two_permitted_for_comparative_signals` | `NEAR_TIE` + one permitted ⇒ not `AMBIGUOUS`; `LOW_CONFIDENCE` + one permitted ⇒ `AMBIGUOUS` (§J.1) |
| 14 | `test_escalation_matches_strategy_not_just_action` | `HOLD_BOTH_PENDING_REVIEW` as `permitted[0]` ⇒ `ESCALATE`, `escalation_matches == ["strategy:HOLD_BOTH_PENDING_REVIEW"]` (§H.2) |
| 15 | `test_flagged_candidate_still_permitted_but_never_selected` | `hold_both-2` appears in `permitted_candidate_ids` while `selected_candidate` is never it |
| 16 | `test_claude_gate_conditions` | each of the four gate conditions independently false ⇒ not invoked, reason recorded (§L.2) |
| 17 | `test_execution_authorized_identical_without_advisor` | `NullAdvisor` vs valid advisor ⇒ same `outcome`, same `execution_authorized` (**constraint 4**) |
| 18 | `test_advisor_raising_is_contained` | advisor raises ⇒ `error UNAVAILABLE`, `fallback_applied HOLD`, outcome unchanged, no exception escapes |
| 19 | `test_advisor_timeout_is_contained` | port returns `None` ⇒ `TIMEOUT` path, outcome unchanged |
| 20 | `test_decision_id_excludes_advisory` | `decision_id` identical across all five advisor states (§P.2) |
| 21 | `test_schema_violation_escalates_but_never_authorizes` | advisory containing `outcome` ⇒ `AMBIGUOUS → ESCALATE`, `output_used False`, `execution_authorized False` (§N.2) |
| 22 | `test_advisor_cannot_introduce_a_candidate` | `suggested_candidate_id` not in `permitted_candidate_ids` ⇒ `SCHEMA_VIOLATION`, advisory discarded |
| 23 | `test_advisory_text_is_inert` | advisory strings containing YAML/JSON/code-looking text appear only in `rationale.claude_narrative`, verbatim, and change nothing else |
| 24 | `test_no_forbidden_imports_in_govern_source` | `ast` walk of `backend/govern/*.py`: no `anthropic`, `requests`, `httpx`, `urllib`, `socket`, `subprocess`, `random`, `uuid`, `time`, `datetime`, `sqlalchemy`, `database` (§L.1, §P.1) |
| 25 | `test_policy_hash_mismatch_raises` | `weigh_output.policy_hash` altered ⇒ `GovernInputError` |
| 26 | `test_audit_required_fields_supplied` | every `policy.audit.required_fields` entry except `timestamp` resolves in the output (§O) |
| 27 | `test_no_timestamp_in_output` | recursive walk finds no `timestamp` / `created_at` / `decided_at` key |
| 28 | `test_govern_weigh_disagreement_escalates` | hand-edited `weigh_output` finding contradicting the re-check ⇒ `ESCALATE`, disagreement recorded (D2) |
| 29 | `test_weigh_output_forbidden_key_rejected` | `weigh_output` carrying a `FORBIDDEN_OUTPUT_KEYS` member ⇒ `GovernInputError` |
| 30 | `test_deterministic_repeated_calls` | `json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True)` |
| 31 | `test_inputs_are_not_mutated` | deepcopy-compare all four inputs before/after |
| 32 | `test_all_candidates_blocked_escalates` | every candidate blocked ⇒ `ESCALATE`, `NO_PERMITTED_CANDIDATE`, all candidates still listed with reasons |
| 33 | `test_unresolved_case_escalates` | synthetic `unresolved: true` / `hold_both_pending_review-1` sole candidate ⇒ `ESCALATE` (§H.2) |
| 34 | `test_profile_selected_reads_profile_name` | reads `profile.profile_name`; a `weigh_output` carrying `selected` is rejected by #29 |
| 35 | `test_policy_change_changes_outcome_without_code_change` | `proceed_min_score` 0.75 → 0.76 on §S.1 ⇒ `PROCEED` → `HOLD`; `policy_hash` differs |

Tests 1–5, 17–22, and 24 are the ones that encode this task's five hard constraints. If time forces a subset, those are the subset.

### U.3 Fixture guidance

Build a `_case()` helper returning `(weigh_output, agent_actions, case_context, policy)` by running the **real** pipeline (`evaluate_agent_actions` → `generate_resolution_candidates` → `evaluate_candidates`), so the numbers in §S stay honest, then mutate one thing per test. For advisor tests, use tiny local fakes — `_ValidAdvisor`, `_RaisingAdvisor`, `_NoneAdvisor`, `_ViolatingAdvisor` — never a network client.

---

## V. Recommended implementation file structure

```
backend/govern/
    __init__.py        # exports decide, GovernInputError, GovernPolicyError, Advisor, NullAdvisor
    govern.py          # decide(): phase sequencing + output assembly. No rules of its own
    permissions.py     # Phase 1: constraint re-check from raw evidence + WEIGH agreement
    authority.py       # Phase 2: the two policy lists + per-agent facts + governance gate
    outcome.py         # Phase 4: the decision table, score bands, ambiguity_applies
    advisor.py         # Advisor Protocol, NullAdvisor, request builder, response validator
    errors.py          # GovernInputError, GovernPolicyError
    schema.py          # GOVERN_VERSION, outcome/basis codes, FALLBACK_OUTCOME_ALIASES,
                       # ADVISORY_FORBIDDEN_KEYS, ADVISOR_REQUEST_FIELDS, REQUIRED_WEIGH_KEYS

    test_govern.py             # end-to-end §S.1/§S.2/§S.3, invariants, determinism (1,2,5,7,8,30,31,35)
    test_permissions.py        # re-check, INDETERMINATE blocking, disagreement (4,9,28,32)
    test_authority.py          # caps, strategy matching, governance gate (3,6,14,15,33)
    test_outcome.py            # decision table, bands, ambiguity gate (10,11,12,13)
    test_advisor.py            # gate, parity, failures, schema violations (16–23)
    test_govern_safety.py      # ast imports, no timestamp, hash mismatch, audit fields (24–27,29,34)
```

Eight source modules, six test modules — the same shape as `backend/weigh/`, which is the house convention the repo already follows.

**Why each module exists** (per the "every abstraction needs a concrete reason" rule):

| Module | Concrete reason |
|---|---|
| `govern.py` | one public entry point; assembly only, so no rule hides inside the orchestration |
| `permissions.py` | Phase 1 is a distinct concern with a distinct test file; it is where "don't trust `weigh_output`" lives |
| `authority.py` | separate **because** authority is precisely what WEIGH reported and GOVERN enforces — the WEIGH/GOVERN boundary becomes visible in the file tree, which matters when presenting |
| `outcome.py` | the decision table is the thing a judge will be shown; it should be readable in one screen without permission logic wrapped around it |
| `advisor.py` | the port boundary. Isolating it is what makes `test_no_forbidden_imports_in_govern_source` meaningful and what keeps Claude removable |
| `errors.py`, `schema.py` | mirror `weigh/`; constants and exception types with no logic |

**Implementation order:** `errors.py` → `schema.py` → `authority.py` → `permissions.py` → `outcome.py` → `advisor.py` → `govern.py`, each with its tests before moving on. `govern.py` last, and it should contain no `if` that decides anything.

**Explicitly out of scope:** the Action Executor, the Decision Receipt, database persistence, API endpoints, orchestration wiring, any UI, HMAC policy signing, and any real Anthropic adapter.

---

## Decision log — what an implementer must not re-litigate

| # | Decision | Section |
|---|---|---|
| 1 | No-conflict skips the **score band only**; constraints, authority, and the governance gate always run | C.3, F.1 (D5) |
| 2 | GOVERN never re-scores; it orders the permitted set by WEIGH's `total_score` | C.2, E.3 |
| 3 | Constraint re-check re-runs the shared evaluators against **raw evidence**, not against `weigh_output` | G.1 |
| 4 | Blocked is the union of both layers; any disagreement forces `ESCALATE` | C.2, F.1 (D2) |
| 5 | `INDETERMINATE` blocks exactly like `VIOLATED` | G.2 |
| 6 | `actions_requiring_escalation` matches **strategy and actions**, evaluated at `permitted[0]`, not at set membership | H.2 |
| 7 | `actions_requiring_governance` requires a per-action `governance_gate` record that must be determinate | H.3 |
| 8 | Amount cap is inclusive (`amount > cap` violates); 50 000 authorized, 50 001 not | H.1, S.3 |
| 9 | Band boundaries inclusive at both ends; 0.7500 proceeds, 0.4000 holds | I.3 |
| 10 | The mid band comes from `escalation.thresholds.mid_band_outcome`; absent ⇒ `GovernPolicyError` at preflight | I.2, R.1 |
| 11 | Decision-table order is D1…D6; `AMBIGUOUS` outranks the band, `ESCALATE` outranks both | F.1 |
| 12 | Comparative ambiguity signals need ≥2 permitted candidates; non-comparative ones do not | J.1 |
| 13 | `execution_authorized = (outcome == "PROCEED")`, assigned in exactly one place | F.1, U.1 |
| 14 | Claude is an injected port; `backend/govern/` never imports an SDK; `ast`-verified | L.1, U.2 #24 |
| 15 | Claude is gated on `AMBIGUOUS` **and** `execution_authorized is False` — never reachable on an authorizing path | L.2 |
| 16 | Advisory text lands only in `rationale.claude_narrative` and is inert | L.4, M.3 |
| 17 | `suggested_candidate_id` must be in `permitted_candidate_ids`; anything else is a schema violation | M.3 |
| 18 | The only post-advisor outcome transition is `AMBIGUOUS → ESCALATE` on `SCHEMA_VIOLATION` | N.2 |
| 19 | `FALLBACK_OUTCOME_ALIASES` bridges `HOLD_FOR_REVIEW` → `HOLD`; fallback values never enter `outcome` directly | N.1 |
| 20 | `decision_id` is a content hash computed in Phase 5, before the advisor exists; no clock, no uuid | P.2 |
| 21 | GOVERN emits no `timestamp`; the orchestrator supplies it | O, P.1 |
| 22 | `profile_selected` reads `weigh_output.profile.profile_name`, never `profile.selected` | 0, O |
| 23 | Policy gaps raise; evidence gaps are reported | Q |
| 24 | `selected_candidate` (authorized) and `candidate_under_review` (top permitted) are different fields | E.1 |

---

**End of design. Nothing in `backend/` was created or modified for this task, and no policy file was edited — every correction in §R is a proposal awaiting approval.**
