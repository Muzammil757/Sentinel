# Sentinel — WEIGH Layer Architecture Design

**Status:** Design only. Not implemented.
**Phase:** 2B (follows 2A policy foundation, commit `475454d`)
**Audience:** the engineer implementing `backend/weigh/`
**Rule for the implementer:** every architectural decision needed to write this layer is fixed below. If you hit a decision this document does not answer, stop and escalate rather than inventing one.

---

## 0. Reading notes and grounding

This design was written against the code as it exists at `475454d`:

| Component | File | What WEIGH depends on |
|---|---|---|
| Agents | `backend/mock_agents/*.py` | `agent`, `proposed_action`, `confidence`, plus domain fields |
| Conflict Matrix | `backend/conflict_matrix/matrix.py`, `integration.py` | `conflict`, `action_a`, `action_b`, `entity_type` |
| RESOLVE | `backend/resolve/resolver.py`, `rules.py` | the candidate list contract |
| Policy | `backend/policy/policy_bundle.yaml`, `loader.py` | objectives, weights, profiles, hard constraints, authority, ambiguity |

Three abbreviations used throughout for the five policy objectives:

| Short | Policy key |
|---|---|
| `fep` | `financial_exposure_prevention` |
| `frr` | `fraud_risk_reduction` |
| `crr` | `compliance_risk_reduction` |
| `mt` | `merchant_trust` |
| `oc` | `operational_cost` |

**Directionality warning that will bite you if you skip it:** every objective is scored as *achievement of the objective*, never as the magnitude of the thing it is named after. `operational_cost` is defined in policy as *"Minimize unnecessary manual review and operational overhead."* Therefore `+1.0` on `operational_cost` means **cheap**, and `-1.0` means **expensive**. `HOLD_BOTH_PENDING_REVIEW` scores strongly *negative* on `operational_cost`. Higher is always better, for all five.

---

## A. WEIGH's responsibility

WEIGH is a **pure evaluation function**. Given a conflict that RESOLVE has already turned into a fixed set of candidate resolutions, WEIGH answers one question:

> Under the currently active governance policy, how does each candidate score against each objective, how confident is the underlying evidence, which candidates appear to trip a hard constraint, and is the comparison close enough to be ambiguous?

Concretely it must:

1. Consume RESOLVE output verbatim.
2. Consume the originating agent payloads, but only through three narrow channels (§T).
3. Consume an already-loaded, already-validated policy dict.
4. Deterministically select the applicable weight profile from an explicit case context.
5. Score every candidate against all five objectives, showing the arithmetic.
6. Aggregate confidence deterministically.
7. Evaluate hard constraints **advisorily** and mark candidates ineligible.
8. Detect ambiguity signals deterministically.
9. Emit a ranking plus complete provenance for the future Decision Receipt.

WEIGH is the layer that makes Sentinel's governance *legible*. Its output must let a judge read the numbers and reconstruct the result by hand.

---

## B. Non-responsibilities

WEIGH must not:

| Must not | Why / where it belongs |
|---|---|
| Emit a final action, decision, selected candidate, winner, or outcome | GOVERN's authority (§E denylist) |
| Execute anything | Action Executor |
| Write to the database or read files | Orchestrator; kills testability and purity |
| Call the network, external APIs, or Claude | GOVERN may invoke bounded Claude; WEIGH never does |
| Invent, merge, split, reword, or drop candidates | RESOLVE owns candidate generation |
| Enforce a hard constraint | GOVERN re-checks independently (§I) |
| Enforce or override authority limits | Reports advisorily only |
| Hard-code any weight, threshold, or impact value | All numbers come from policy (§K) |
| Infer merchant risk tier, fraud likelihood, RTO risk, or churn risk | This is the Open Track trap (§T) |
| Read the clock, use randomness, or depend on dict/set iteration order | Determinism (§O) |
| Re-validate the whole policy bundle | `policy.loader` already did; WEIGH asserts only the sections it uses |

---

## C. The RESOLVE → WEIGH → GOVERN contract

### C.1 Shape of the pipeline

```
conflict_matrix.integration.evaluate_agent_actions(a, b, entity_type)
        │  conflict_result
        ▼
resolve.resolver.generate_resolution_candidates(conflict_result, a_detail, b_detail)
        │  resolve_output  ─────────────────────────────┐
        ▼                                                │ (unchanged, passed through)
weigh.evaluate_candidates(resolve_output,                │
                          agent_actions,                 │
                          case_context,                  │
                          policy)                        │
        │  weigh_output  ◄──────────────────────────────┘
        ▼
govern.decide(weigh_output, agent_actions, case_context, policy)
        │  governed_outcome  (the ONLY layer that names a winner)
        ▼
executor → decision receipt
```

### C.2 Contract invariants (each is a test in §P)

1. **Candidate set is closed.** `{c.candidate_id for c in weigh_output.candidates}` is exactly equal to the set from `resolve_output`. No additions, no removals, no renaming.
2. **Candidate substance is immutable.** For each candidate, `strategy`, `preferred_agent`, `resulting_actions`, `source_rule`, and `rationale` are copied through byte-identically. WEIGH only *adds* fields.
3. **No decision field.** WEIGH output contains no key from the denylist in §E.6, at any nesting depth.
4. **Constraint findings are advisory.** Every finding carries `"advisory": true`, and the output carries `constraint_evaluation.authority == "advisory_only"` and `rechecked_by == "GOVERN"`.
5. **Policy identity travels with the numbers.** `policy_id`, `policy_version`, `policy_hash` are always present, and the hash is computed from the policy dict actually used.
6. **Purity.** Same four inputs ⇒ byte-identical output.

### C.3 Interface caveat GOVERN must honour (important — read this before writing GOVERN)

`total_score` is a **comparative quantity within a single case**, not an absolute safety rating. Two consequences:

- **Do not threshold single-candidate cases.** Policy's `escalation.thresholds.proceed_min_score: 0.75` is meaningful only when there is a real choice. A `NO_CONFLICT_PROCEED` case scores whatever its actions happen to score — worked example in §Q.4 gives `0.3100` for a perfectly benign "release payment, close case" pair — because `RELEASE_PAYMENT` is intrinsically negative on `financial_exposure_prevention`. Applying `proceed_min_score` there would hold a case in which no agent disagreed with anything. **GOVERN must short-circuit `case.conflict == false` before scoring thresholds apply.**
- **Do not compare scores across cases.** Different candidate sets, different action mixes. Scores are ordinal within a case.

WEIGH surfaces this by echoing `case.conflict` and `case.unresolved` at the top level, and by setting the `SINGLE_CANDIDATE` informational signal.

### C.4 RESOLVE stays as it is — with one recommended additive change

This design requires **zero changes to RESOLVE to function**. However, a finding worth the team's attention:

> With RESOLVE's current output, the weight profile can change the *scores* but almost never the *ordering*, because both candidates sit on the same side of the risk/trust trade-off.

RESOLVE emits, for a known conflict, exactly two candidates: `DEFER_TO_AGENT` toward the **higher-priority** (always the more conservative) agent, and `HOLD_BOTH_PENDING_REVIEW`. `AGENT_PRIORITY_ORDER = [dispute, rto, payouts, retention]` guarantees the deferred-to agent is the cautious one. So WEIGH is asked to choose between "cautious" and "even more cautious", and no weight profile flips that.

**Recommendation (requires your approval; not assumed by this design):** RESOLVE additionally emits the counterfactual `defer_to_agent-2` — `DEFER_TO_AGENT` toward the *non*-preferred agent. It is additive (new `candidate_id`, existing candidates untouched), backward compatible, and WEIGH handles it with no code change.

Without it, §R demo variant A works (ambiguity flips). With it, §R demo variant B works (the ranking fully reverses), which is the far stronger stage moment. §R states which examples depend on it.

---

## D. Input schema

### D.1 Signature

```python
def evaluate_candidates(
    resolve_output: dict,   # verbatim from resolve.resolver.generate_resolution_candidates
    agent_actions: dict,    # {agent_name: agent_payload}
    case_context: dict,     # explicit governance facts; NEVER inferred from evidence
    policy: dict,           # already loaded + validated by policy.loader.load_policy
) -> dict:
```

Four positional-or-keyword arguments, no defaults, no globals, no module-level state.

### D.2 `resolve_output`

Consumed exactly as produced today:

```python
{
  "entity_type": "order_vendor",
  "agent_a": "payouts",
  "agent_b": "dispute",
  "conflict": True,
  "unresolved": False,
  "candidates": [
    {
      "candidate_id": "defer_to_agent-1",
      "strategy": "DEFER_TO_AGENT",
      "preferred_agent": "dispute",
      "resulting_actions": ["HOLD_RELATED_ACTIONS"],
      "rationale": "...",
      "source_rule": "release_payment_vs_hold_related_actions",
    },
    ...
  ],
}
```

### D.3 `agent_actions` — a mapping, not a positional pair

```python
{
  "payouts": {"agent": "payouts", "proposed_action": "RELEASE_PAYMENT", "confidence": 0.95, "amount": 42000, ...},
  "dispute": {"agent": "dispute", "proposed_action": "HOLD_RELATED_ACTIONS", "confidence": 0.95, "dispute_status": "OPEN", ...},
}
```

Rationale for diverging from RESOLVE's `(action_a_detail, action_b_detail)` positional pair:

- Constraint predicates need to look up an agent **by role** ("what does the dispute agent say?"), not by whichever slot it landed in.
- It removes an ordering-dependence source: WEIGH's result cannot depend on which agent happened to be `a` vs `b`. That is a determinism win.
- It generalises to N agents without a signature change.

The orchestrator builds this map trivially: `{d["agent"]: d for d in (a_detail, b_detail)}`. RESOLVE's contract is untouched.

### D.4 `case_context` — explicit governance facts only

```python
{
  "case_id": "case-2026-08-24-0007",      # optional; echoed if present, NEVER generated
  "merchant_id": "mrch_001",              # optional; echoed
  "merchant_risk_tier": "high",           # drives profile_selection
  "merchant_trust_tier": "trusted",       # drives profile_selection
  "merchant_flags": ["FRAUD_REVIEW"],     # drives HC_RETENTION_TO_FLAGGED_MERCHANT
}
```

**This is the single most important boundary in the design.** These are *configured facts about the merchant relationship*, supplied by the caller from merchant configuration. WEIGH must **never** derive `merchant_risk_tier` from `rto_score`, `churn_risk`, `disputed_amount`, or any other agent evidence. Doing so would make Sentinel a risk classifier (§T).

All keys optional. Empty dict is valid and yields the default profile. Unknown keys are ignored.

### D.5 `policy`

The dict returned by `policy.loader.load_policy()`. WEIGH:

- treats it as **read-only** and never mutates it;
- does **not** re-run full validation (`load_policy` did that);
- **does** assert the presence of the sections it consumes, raising `WeighPolicyError` on absence;
- does **not** load it from disk itself — dependency injection keeps WEIGH file-I/O-free and lets tests pass a mutated copy.

### D.6 Input validation — fail loudly, never fail silently

Raise `WeighInputError` (subclass of `ValueError`) with a deterministic message when:

- `resolve_output` is missing any of `entity_type / agent_a / agent_b / conflict / unresolved / candidates`;
- `candidates` is empty or not a list;
- any candidate is missing any of `candidate_id / strategy / preferred_agent / resulting_actions / rationale / source_rule`;
- `candidate_id` values are not unique within the output;
- `agent_a` or `agent_b` is absent from `agent_actions`;
- a candidate's `preferred_agent` is not `None` and not present in `agent_actions`;
- `case_context` is not a mapping.

Never substitute a default and continue. An integration bug must not be quietly governed.

> Note on candidate id uniqueness: RESOLVE's ids are unique *within one output* but not globally (`hold_both_pending_review-1` on the unresolved path, `-2` on the rule path — they never co-occur). The audit layer must therefore key candidates by `(case_id, candidate_id)`. WEIGH asserts within-output uniqueness and nothing more.

---

## E. Output schema

### E.1 Top level

```python
{
  "weigh_version": "1.0.0",
  "scoring_method": "weighted_linear_v1",

  "policy_id": "sentinel_demo_policy_v1",
  "policy_version": "1.1.0",
  "policy_hash": "3f2c…",                       # sha256 of the policy actually used

  "case": {
    "case_id": "case-2026-08-24-0007",          # omitted entirely if not supplied
    "entity_type": "order_vendor",
    "agent_a": "payouts",
    "agent_b": "dispute",
    "conflict": true,
    "unresolved": false
  },

  "profile": {
    "selected": "high_risk_merchant",
    "reason": "matched_rule",                   # "matched_rule" | "default"
    "matched_rule_index": 0,                    # null when reason == "default"
    "matched_rule": {"when": {"merchant_risk_tier": "high"}, "profile": "high_risk_merchant"},
    "weights": {                                # verbatim from policy, alphabetical
      "compliance_risk_reduction": 0.20,
      "financial_exposure_prevention": 0.30,
      "fraud_risk_reduction": 0.35,
      "merchant_trust": 0.05,
      "operational_cost": 0.10
    }
  },

  "evidence": { ... },                          # §E.2
  "candidates": [ ... ],                        # §E.3, in RESOLVE's original order
  "ranking": [ ... ],                           # §E.4
  "ambiguity": { ... },                         # §E.5
  "constraint_evaluation": { ... },             # §I.4
  "notes": [ ... ]                              # §N.4
}
```

### E.2 `evidence`

```python
"evidence": {
  "contributing_agents": ["dispute", "payouts"],     # sorted, deduped
  "agent_evidence": {                                # ONLY the fields WEIGH consumed
    "dispute": {"proposed_action": "HOLD_RELATED_ACTIONS", "confidence": 0.95},
    "payouts": {"proposed_action": "RELEASE_PAYMENT",      "confidence": 0.95}
  },
  "case_confidence": 0.95,
  "confidence_method": "min_blend_v1",
  "confidence_inputs": {"min": 0.95, "mean": 0.95, "min_weight": 0.5},
  "supporting_signals": 2,
  "evidence_complete": true
}
```

`agent_evidence` records **exactly the fields WEIGH read** — no more. This is the auditable claim ("here is what the scorer looked at"), and it keeps the output snapshot-testable. Agent timestamps are deliberately **not** copied: the receipt layer can join back to raw payloads by agent name, and excluding them keeps WEIGH output stable under repeated pipeline runs.

### E.3 Per-candidate evaluation

```python
{
  # --- copied verbatim from RESOLVE ---
  "candidate_id": "defer_to_agent-1",
  "strategy": "DEFER_TO_AGENT",
  "preferred_agent": "dispute",
  "resulting_actions": ["HOLD_RELATED_ACTIONS"],
  "rationale": "Static agent priority order favors 'dispute' …",
  "source_rule": "release_payment_vs_hold_related_actions",

  # --- added by WEIGH ---
  "objective_impacts": {
    "compliance_risk_reduction": {
      "raw": 0.60, "normalized": 0.80, "weight": 0.20,
      "contribution": 0.1600, "source": "action:HOLD_RELATED_ACTIONS"
    },
    "financial_exposure_prevention": {
      "raw": 0.90, "normalized": 0.95, "weight": 0.30,
      "contribution": 0.2850, "source": "action:HOLD_RELATED_ACTIONS"
    },
    "fraud_risk_reduction": {
      "raw": 0.70, "normalized": 0.85, "weight": 0.25,
      "contribution": 0.2125, "source": "action:HOLD_RELATED_ACTIONS"
    },
    "merchant_trust": {
      "raw": -0.30, "normalized": 0.35, "weight": 0.15,
      "contribution": 0.0525, "source": "action:HOLD_RELATED_ACTIONS"
    },
    "operational_cost": {
      "raw": -0.20, "normalized": 0.40, "weight": 0.10,
      "contribution": 0.0400, "source": "action:HOLD_RELATED_ACTIONS"
    }
  },
  "total_score": 0.7500,

  "originating_agent": "dispute",
  "originating_confidence": 0.95,

  "constraint_findings": [ ... ],                # §I.2
  "eligible": true,
  "eligibility_basis": "no_blocking_findings",   # or "blocked_by:HC_…,HC_…"
  "evidence_complete": true
}
```

`objective_impacts[o].source` records **which** action's vector won the element-wise minimum (`"action:HOLD_ORDER"` or `"strategy:HOLD_BOTH_PENDING_REVIEW"`). This is what lets a receipt say *"the compliance score came from the dispute hold."*

Objective keys are emitted **sorted alphabetically** — canonical, hashable, implementation-independent. The UI may reorder for display.

### E.4 `ranking`

```python
"ranking": [
  {"candidate_id": "hold_both_pending_review-2", "rank": 1, "score_rank": 2,
   "total_score": 0.5175, "eligible": true,  "tie_group": 1},
  {"candidate_id": "defer_to_agent-1",          "rank": 2, "score_rank": 3,
   "total_score": 0.4975, "eligible": true,  "tie_group": 1},
  {"candidate_id": "defer_to_agent-2",          "rank": 3, "score_rank": 1,
   "total_score": 0.5900, "eligible": false, "tie_group": null}
]
```

**Sort key, in order:**

1. `eligible` descending (True before False)
2. `total_score` descending
3. `candidate_id` ascending (lexical)

Two deliberate properties:

- **`ranking[0]` is never a constrained candidate.** A naive `GOVERN` that reaches for the top of the list cannot pick a blocked option. Defence in depth — it does not replace GOVERN's own re-check.
- **`score_rank` preserves the pure-score story.** The blocked candidate above still shows `score_rank: 1`, so the receipt can say *"scored highest, blocked by HC_RETENTION_TO_FLAGGED_MERCHANT."* That is exactly the narrative §S needs.

**Ties carry no meaning.** The `candidate_id` tiebreak is presentational only; it exists so the output is byte-stable. A tie in `total_score` is reported as ambiguity and resolved by GOVERN, never by the sort. Confidence is explicitly **not** used as a tiebreaker — that would be a hidden decision.

`tie_group` is a 1-based integer shared by all eligible candidates inside the near-tie band, `null` otherwise.

WEIGH never removes a candidate from `ranking`. Everything RESOLVE produced appears, with its reason.

### E.5 `ambiguity`

```python
"ambiguity": {
  "detected": true,
  "signals": [
    {"code": "NEAR_TIE",
     "detail": {"top_gap": 0.0200, "threshold": 0.05,
                "members": ["defer_to_agent-1", "hold_both_pending_review-2"]}},
    {"code": "LOW_CONFIDENCE",
     "detail": {"case_confidence": 0.5375, "threshold": 0.55}}
  ],
  "near_tie_group": ["defer_to_agent-1", "hold_both_pending_review-2"],
  "top_gap": 0.0200,
  "near_tie_threshold": 0.05
}
```

The field is `detected`, **not** `status`. `AMBIGUOUS` is a value in `policy.escalation.outcomes` — an *outcome GOVERN assigns*. WEIGH must never emit an escalation outcome, so the token is deliberately avoided here.

`signals` is sorted by `code` for stability. `top_gap` is `null` when fewer than two eligible candidates exist.

### E.6 Forbidden output keys

At **any** nesting depth, WEIGH output must never contain:

```
final_action, decision, selected_candidate, selected, winner, chosen_candidate,
recommended_action, recommendation, action_to_execute, execute, outcome, verdict,
approved, resolution
```

`outcome` is on the list specifically because it is policy vocabulary for GOVERN's result. §P has a recursive test asserting this.

---

## F. Candidate scoring formula

Four steps. A judge should absorb this in under a minute.

**Step 1 — pick the impact vector.**

> A candidate's raw objective vector is the element-wise **minimum over its resulting actions'** vectors. If the candidate has no resulting actions, its **strategy** vector is used instead.

```
                ⎧ min over a ∈ c.resulting_actions of  action_effects[a][o]     if resulting_actions ≠ []
I(c, o)   =     ⎨
                ⎩ strategy_effects[c.strategy][o]                               if resulting_actions == []
```

Element-wise minimum = **the most conservative signal governs**. A benign action can never dilute a risky one bundled with it. This is the same principle applied to confidence in §H — one idea, used twice.

Both tables are needed and neither is redundant: `strategy` alone cannot distinguish "defer to dispute (hold)" from "defer to payouts (release)" — both are `DEFER_TO_AGENT`; actions alone cannot score `HOLD_BOTH_PENDING_REVIEW`, which RESOLVE emits with `resulting_actions: []`.

**Step 2 — normalize.** `N(c, o) = (I(c, o) + 1) / 2`, mapping `[-1, +1] → [0, 1]`.

**Step 3 — weight.** `K(c, o) = round(w(o) × N(c, o), 4)` where `w` is the selected profile's weight for `o`.

**Step 4 — total.** `S(c) = round(Σ_o K(c, o), 4)`.

Because `Σ_o w(o) = 1` (enforced by the loader, ±0.01) and `N ∈ [0, 1]`, `S(c) ∈ [0, 1]` — directly comparable to policy's `proceed_min_score` / `hold_max_score` scale, subject to the §C.3 caveat.

### F.1 Rounding — and why the total is the sum of *rounded* contributions

Contributions are rounded to 4 dp **first**, and the total is the rounded sum of those rounded contributions. The alternative (sum unrounded, round at the end) is marginally more precise but can produce a displayed total that does not equal the sum of the displayed contributions — unacceptable in an auditable system whose whole pitch is "check our arithmetic". **Auditability beats 1e-4 of precision.** §P asserts `sum(contributions) == total_score` exactly.

Author all policy numbers at ≤2 decimal places so products stay well inside float precision. If exactness ever becomes contentious, the hardening path is `decimal.Decimal` with a fixed context — not needed now.

### F.2 Confidence does not enter this formula

Deliberate. See §H.4.

---

## G. Objective normalization and the effect tables

### G.1 Where the numbers live

Both tables live in **policy**, in a new additive `scoring:` section. WEIGH contains no impact constant. This is what makes §R possible.

```yaml
scoring:
  method: weighted_linear_v1
  impact_scale: [-1.0, 1.0]

  confidence:
    method: min_blend_v1
    min_weight: 0.50            # alpha in §H

  action_effects:
    #                       fep     frr     crr      mt      oc
    RELEASE_PAYMENT:      {financial_exposure_prevention: -0.80, fraud_risk_reduction: -0.60, compliance_risk_reduction: -0.30, merchant_trust:  0.70, operational_cost:  0.50}
    HOLD_RELATED_ACTIONS: {financial_exposure_prevention:  0.90, fraud_risk_reduction:  0.70, compliance_risk_reduction:  0.60, merchant_trust: -0.30, operational_cost: -0.20}
    CLOSE_CASE:           {financial_exposure_prevention:  0.10, fraud_risk_reduction:  0.00, compliance_risk_reduction:  0.30, merchant_trust:  0.20, operational_cost:  0.40}
    HOLD_ORDER:           {financial_exposure_prevention:  0.70, fraud_risk_reduction:  0.60, compliance_risk_reduction:  0.20, merchant_trust: -0.80, operational_cost: -0.20}
    REVIEW_ORDER:         {financial_exposure_prevention:  0.30, fraud_risk_reduction:  0.40, compliance_risk_reduction:  0.10, merchant_trust: -0.20, operational_cost: -0.50}
    ALLOW_ORDER:          {financial_exposure_prevention: -0.40, fraud_risk_reduction: -0.50, compliance_risk_reduction: -0.10, merchant_trust:  0.50, operational_cost:  0.40}
    WIN_BACK_OFFER:       {financial_exposure_prevention: -0.30, fraud_risk_reduction: -0.40, compliance_risk_reduction: -0.20, merchant_trust:  0.90, operational_cost:  0.30}
    RETENTION_MESSAGE:    {financial_exposure_prevention:  0.00, fraud_risk_reduction: -0.10, compliance_risk_reduction:  0.00, merchant_trust:  0.50, operational_cost:  0.20}
    NO_RETENTION_ACTION:  {financial_exposure_prevention:  0.00, fraud_risk_reduction:  0.00, compliance_risk_reduction:  0.00, merchant_trust: -0.20, operational_cost:  0.30}

  strategy_effects:
    HOLD_BOTH_PENDING_REVIEW: {financial_exposure_prevention: 0.60, fraud_risk_reduction: 0.50, compliance_risk_reduction: 0.50, merchant_trust: -0.50, operational_cost: -0.90}
    NO_CONFLICT_PROCEED:      {financial_exposure_prevention: 0.00, fraud_risk_reduction: 0.00, compliance_risk_reduction: 0.00, merchant_trust:  0.00, operational_cost:  0.00}
    DEFER_TO_AGENT:           {financial_exposure_prevention: 0.00, fraud_risk_reduction: 0.00, compliance_risk_reduction: 0.00, merchant_trust:  0.00, operational_cost:  0.00}
    SUPPRESS_ACTION:          {financial_exposure_prevention: 0.00, fraud_risk_reduction: 0.00, compliance_risk_reduction: 0.00, merchant_trust:  0.00, operational_cost:  0.00}
```

Normalized reference values (`(raw+1)/2`), used by every worked example below:

| vector | fep | frr | crr | mt | oc |
|---|---|---|---|---|---|
| `RELEASE_PAYMENT` | 0.10 | 0.20 | 0.35 | 0.85 | 0.75 |
| `HOLD_RELATED_ACTIONS` | 0.95 | 0.85 | 0.80 | 0.35 | 0.40 |
| `CLOSE_CASE` | 0.55 | 0.50 | 0.65 | 0.60 | 0.70 |
| `HOLD_ORDER` | 0.85 | 0.80 | 0.60 | 0.10 | 0.40 |
| `WIN_BACK_OFFER` | 0.35 | 0.30 | 0.40 | 0.95 | 0.65 |
| `HOLD_BOTH_PENDING_REVIEW` (strategy) | 0.80 | 0.75 | 0.75 | 0.25 | 0.05 |

### G.2 These are governance preferences, not risk estimates

An effect vector is a **declared policy stance about a category of action** — "releasing money scores badly on financial exposure." It is not a statement about this merchant, this order, or this customer. Nothing in the table is derived from evidence, and nothing in it is fitted, learned, or tuned to observed outcomes. §T depends on this.

### G.3 Required policy-file changes (Phase 2B, needs approval)

Per instruction, `policy_bundle.yaml` was **not** modified. The implementer will need to:

1. Add the `scoring:` section above to `backend/policy/policy_bundle.yaml`.
2. Add a `scoring` property to `backend/policy/policy_schema.json`, and to its top-level `required` array. (The schema has no `additionalProperties: false`, so an unlisted section would silently pass — listing it as required is what makes the dependency enforced.)
3. Bump `policy.version` to `"1.1.0"` — the bundle gains a section WEIGH cannot run without.
4. Extend `policy/loader.py` with `_validate_scoring()`: every vector's keys equal the objective set; every value numeric and within `[-1, +1]`; `confidence.min_weight` numeric in `[0, 1]`; `method` present.
5. **Separately recommended loader hardening, currently missing:** validate that every `profile_selection.rules[].profile` and `profile_selection.default_profile` actually exists in `weights.profiles`. Today a rule can name a nonexistent profile and pass validation. WEIGH will fail closed on this (§L.3), but catching it at load time is better.

---

## H. Confidence

### H.1 The proposed formula is degenerate — do not implement it

The brief proposes *"a weighted mean floored by the minimum contributing confidence."* Both readings collapse:

| reading | result | why |
|---|---|---|
| `max(weighted_mean, min)` | `= weighted_mean`, always | the mean is **always ≥** the minimum, so the floor never binds — it is a no-op |
| `min(weighted_mean, min)` | `= min`, always | for the same reason, the mean is discarded entirely |

Worked: contributions `{rto: 0.40, retention: 0.95}` → mean `0.675`, min `0.40`. `max(0.675, 0.40) = 0.675` (mean, floor irrelevant). `min(0.675, 0.40) = 0.40` (min, mean irrelevant). Either way one of the two terms is dead weight, and the stated principle is not actually enforced.

### H.2 Recommended mechanism — `min_blend_v1`

Keep the mean's information *and* let the weakest input genuinely drag the result down, by blending rather than clamping:

```
A            = sorted set of contributing agents (agent_a, agent_b, deduped)
c_i          = agent i's declared confidence, validated numeric in [0, 1]
C_min        = min(c_i)
C_mean       = (Σ c_i) / |A|
α            = policy.scoring.confidence.min_weight        (0.50 in the demo bundle)

case_confidence = round( α · C_min + (1 − α) · C_mean , 4 )
```

Worked on the same numbers, α = 0.5: `0.5 × 0.40 + 0.5 × 0.675 = 0.5375`. The confident agent's 0.95 no longer hides the weak 0.40, and the 0.40 does not erase the 0.95 either.

Properties worth stating in the receipt:

- `C_min ≤ case_confidence ≤ C_mean` — always strictly between, never degenerate.
- **Monotone non-decreasing in every input:** `∂C/∂c_j = (1−α)/n + α·[j is the argmin] ≥ 0`. Raising any agent's confidence can never lower the aggregate. (A pure-min rule fails this in spirit; a pure mean fails the brief's principle.)
- At `α = 1` it is pure worst-case; at `α = 0`, pure mean. **α is a policy knob**, so the demo can tune conservatism without touching code.
- With a single contributing agent, `case_confidence == c_1` exactly.

The mean is **unweighted**. The brief says "weighted mean", but there is no principled weight available — weighting by agent priority or by which agent a candidate prefers would inject an opaque judgment into a number the receipt has to defend. Simplicity here is a correctness property, not laziness.

### H.3 Two confidences, because policy asks two different questions

`policy.hard_constraints[HC_CONFIDENCE_FLOOR].description` says *"below **its originating agent's** confidence"*, while `policy.ambiguity.low_confidence_threshold` is about the case as a whole. So:

| quantity | scope | definition | consumed by |
|---|---|---|---|
| `case_confidence` | the case | `min_blend_v1` over contributing agents | `LOW_CONFIDENCE` ambiguity signal |
| `originating_confidence` | per candidate | confidence of the candidate's `preferred_agent`; falls back to `case_confidence` when `preferred_agent is None` | `HC_CONFIDENCE_FLOOR` |

**Contributing agents = the agents party to the conflict (`agent_a`, `agent_b`), for every candidate.** Including both even on a `DEFER_TO_AGENT` candidate is deliberate: *suppressing* agent B's recommendation is itself a governed act, and how sure B was is material to whether suppressing it is safe. If B was 0.30-confident a hold is needed, deferring to A is a different proposition than if B was 0.99-confident. This is exactly the principle the brief asked for, and it is why `case_confidence` is uniform across candidates — confidence describes the *evidence*, not the *option*.

### H.4 Confidence must not multiply the score

Three reasons, in priority order:

1. **It would break GOVERN.** Confidence is already a hard constraint (`HC_CONFIDENCE_FLOOR`), an ambiguity threshold, and an escalation input. Baked into the score, GOVERN cannot apply those cleanly and the receipt cannot separate "this was a bad option" from "we were unsure."
2. **It conflates two different claims.** "How good is this option" and "how sure are we" are orthogonal; a product of them is uninterpretable.
3. **It hides a governance smell.** Multiplication lets a high-confidence poor option arithmetically beat a low-confidence good option, with no visible trace.

Score and confidence travel **side by side**. Confidence is a **gate**, never a multiplier, and never a tiebreaker.

### H.5 Missing or invalid confidence

Absent, non-numeric, or out-of-`[0,1]` confidence for a contributing agent ⇒ treated as **`0.0`**, plus a `notes` entry `E_MISSING_CONFIDENCE`, plus `evidence_complete: false`.

This is conservative by construction and needs no new machinery: `0.0` is below `HC_CONFIDENCE_FLOOR`'s `min_confidence: 0.60`, so any candidate that would actually execute an action gets marked ineligible, and GOVERN escalates. The house rule from `policy.fallback` — never PROCEED on degraded input — is preserved automatically.

---

## I. Hard-constraint representation

### I.1 The safety architecture

```
WEIGH   →  "Candidate defer_to_agent-2 appears to violate HC_RETENTION_TO_FLAGGED_MERCHANT."   (advisory)
GOVERN  →  independently re-evaluates every constraint from policy + raw evidence,
           and blocks the unsafe action on its own finding.                                     (authoritative)
```

GOVERN must **not** trust `weigh_output.candidates[].eligible`. It re-derives constraint status from `policy` and `agent_actions` itself. WEIGH's findings exist so the receipt can show the reasoning and so ambiguity/ranking are sensible — they are never the enforcement point. Every finding is stamped `advisory: true` so this is visible **in the data**, not just in documentation.

### I.2 Finding structure

```python
{
  "constraint_id": "HC_PAYOUT_DURING_CHARGEBACK",
  "status": "VIOLATED",                  # VIOLATED | SATISFIED | NOT_APPLICABLE | INDETERMINATE
  "enforcement": "block",                # copied from policy; never invented
  "predicate": "'RELEASE_PAYMENT' in candidate.resulting_actions AND dispute.dispute_status in {OPEN, UNDER_REVIEW}",
  "observed": {"resulting_actions": ["RELEASE_PAYMENT"], "dispute.dispute_status": "OPEN"},
  "parameters": {},                      # from policy.hard_constraints[].parameters, if any
  "source": "policy.hard_constraints[0]",
  "advisory": true
}
```

`predicate` is a **human-readable description string**, not an executable expression. Nothing in WEIGH parses or evaluates strings. This mirrors the loader's existing stance (`test_no_eval_or_dynamic_execution`).

### I.3 The four statuses — and why `INDETERMINATE` is not `SATISFIED`

| status | meaning | eligibility effect |
|---|---|---|
| `NOT_APPLICABLE` | the guarded action is not in this candidate; no evidence needed | none |
| `SATISFIED` | checked against present evidence; constraint holds | none |
| `VIOLATED` | checked against present evidence; constraint breached | **blocks** |
| `INDETERMINATE` | the guarded action *is* present but required evidence is absent or unusable | **blocks** |

Never report `SATISFIED` for a check that could not be performed. `INDETERMINATE` blocks (conservative) while remaining distinguishable from `VIOLATED` in the receipt — the difference between *"we checked and it's bad"* and *"we couldn't check"* matters to a human reviewer and to a future bounded-Claude prompt.

`eligible = not any(f.status in {VIOLATED, INDETERMINATE} for f in findings)`.

### I.4 `constraint_evaluation` block

```python
"constraint_evaluation": {
  "authority": "advisory_only",
  "rechecked_by": "GOVERN",
  "constraints_checked": ["HC_CONFIDENCE_FLOOR", "HC_PAYOUT_DURING_CHARGEBACK",
                          "HC_RETENTION_TO_FLAGGED_MERCHANT",
                          "HC_THIRDWATCH_HIGH_RISK_PAYOUT", "HC_UNAUTHORIZED_ACTION"],
  "violated_candidate_ids": ["defer_to_agent-2"],
  "indeterminate_candidate_ids": []
}
```

Lists sorted, for byte-stability.

### I.5 The "no action, no violation" invariant

> A hard constraint gates an **action**. A candidate with `resulting_actions == []` executes nothing, and therefore cannot violate an action-gating constraint.

`HOLD_BOTH_PENDING_REVIEW` is thus always `NOT_APPLICABLE` on every constraint, including `HC_CONFIDENCE_FLOOR`. This is not a convenience — it is a required safety property:

- Without it, low case confidence would mark the *conservative fallback* ineligible, and a case could end with **zero** eligible candidates purely because the evidence was weak. That is backwards: uncertainty should make you hold, not make holding unavailable.
- With it, **whenever RESOLVE emits a `HOLD_BOTH_PENDING_REVIEW` candidate, the eligible set is guaranteed non-empty.**

The remaining empty-set case is the single-candidate `NO_CONFLICT_PROCEED` path, which correctly raises `ALL_CANDIDATES_CONSTRAINED` (§J.2).

### I.6 Evaluators live in code; thresholds live in policy

A registry keyed by constraint id:

```python
CONSTRAINT_EVALUATORS = {
    "HC_PAYOUT_DURING_CHARGEBACK":      _eval_payout_during_chargeback,
    "HC_THIRDWATCH_HIGH_RISK_PAYOUT":   _eval_thirdwatch_high_risk_payout,
    "HC_RETENTION_TO_FLAGGED_MERCHANT": _eval_retention_to_flagged_merchant,
    "HC_CONFIDENCE_FLOOR":              _eval_confidence_floor,
    "HC_UNAUTHORIZED_ACTION":           _eval_unauthorized_action,
}
```

Each evaluator has the pure signature `(candidate, agent_actions, case_context, constraint, case_confidence) -> finding`.

**Why code, not a policy DSL:** a declarative predicate language would need a parser, a validator, and a security review, and would tempt someone toward `eval`. Named evaluators keep *logic* in reviewed, tested code while all *numbers* stay in policy. Honest trade-off: **constraint logic is not policy-tunable in this design** — the demo's "change one policy parameter" story runs through weights and thresholds (§R), not through constraint logic.

**Fail-closed startup check (required):** before scoring, assert that every `policy.hard_constraints[].id` has a registered evaluator. If policy adds a constraint WEIGH cannot evaluate, raise `WeighPolicyError` — never silently skip it. A constraint that exists in policy but is invisible at runtime is the worst failure mode this system has.

### I.7 Evaluator notes for the five constraints

| Constraint | Evidence used | Notes |
|---|---|---|
| `HC_PAYOUT_DURING_CHARGEBACK` | `RELEASE_PAYMENT ∈ resulting_actions`; `agent_actions["dispute"]["dispute_status"]` | `INDETERMINATE` if no dispute agent in the case or the field is missing |
| `HC_THIRDWATCH_HIGH_RISK_PAYOUT` | `RELEASE_PAYMENT ∈ resulting_actions`; the **RTO agent's own verdict** | See §I.8 |
| `HC_RETENTION_TO_FLAGGED_MERCHANT` | `WIN_BACK_OFFER ∈ resulting_actions`; `case_context["merchant_flags"]` | `INDETERMINATE` if `merchant_flags` absent |
| `HC_CONFIDENCE_FLOOR` | `originating_confidence` vs `parameters.min_confidence` | Strict `<` violates ("below the floor"). `NOT_APPLICABLE` when `resulting_actions == []` (§I.5) |
| `HC_UNAUTHORIZED_ACTION` | each action ∈ `authority.agents[agent].autonomous_actions`; amount vs `max_autonomous_amount` | `max_autonomous_amount: null` ⇒ no amount check. Amount required but absent ⇒ `INDETERMINATE` (e.g. retention's 5000 cap with no amount field on the payload) |

### I.8 Single source of risk truth

`HC_THIRDWATCH_HIGH_RISK_PAYOUT` must key off **the RTO agent's own published verdict** (`agent_actions["rto"]["proposed_action"] == "HOLD_ORDER"`), not off a threshold WEIGH applies to `rto_score`.

Re-deriving a risk band inside WEIGH would create a *second* risk classifier that can silently disagree with the agent that owns the question — and that is precisely the drift into "AI Risk Manager" that §T forbids.

If an agent ever fails to publish a band and a numeric threshold is genuinely unavoidable, the threshold goes in `policy.hard_constraints[].parameters` and must **mirror** the agent's own published cutoff (`rto.py` uses `>= 0.75`). §P includes a mirror-consistency test so the two cannot drift apart unnoticed.

---

## J. Ambiguity

All thresholds come from `policy.ambiguity`. WEIGH **detects and reports**; GOVERN decides what it means.

### J.1 Near-tie: absolute gap, top-of-band grouping

```
E                = eligible candidates, sorted by total_score descending
S_top            = S(E[0])
near_tie_group   = [ c ∈ E : S_top − S(c) ≤ policy.ambiguity.near_tie_threshold ]   # inclusive ≤
NEAR_TIE         ⟺ len(near_tie_group) ≥ 2
top_gap          = S(E[0]) − S(E[1])                                                # null if len(E) < 2
```

**Absolute gap only. A relative gap is not needed** — asked and answered:

- The score space is already normalized to `[0, 1]` with `Σw = 1`, so an absolute gap is dimensionally meaningful and behaves identically everywhere on the scale.
- A relative gap (`gap / S_top`) would make the same threshold mean different things at the top and bottom of the range, and would require a second explanation on stage.
- Escape hatch if it is ever needed: add `ambiguity.near_tie_mode: absolute | relative` to policy. Do not build it now.

**How many candidates:** `NEAR_TIE` is triggered by the top two, but the *group* includes every eligible candidate within the threshold of the leader, so a three-way cluster is reported honestly rather than truncated. Each `ranking` entry also carries `tie_group` so GOVERN sees the exact membership.

Boundary: `≤` is a tie (a gap exactly equal to the threshold is ambiguous). Fixed, and tested at the boundary.

### J.2 The six signals

| Code | Condition | Sets `detected` |
|---|---|---|
| `NEAR_TIE` | §J.1 | yes |
| `LOW_CONFIDENCE` | `case_confidence < policy.ambiguity.low_confidence_threshold` (0.55) | yes |
| `INSUFFICIENT_EVIDENCE` | `supporting_signals < policy.ambiguity.insufficient_evidence.min_supporting_signals` (1), **or** any candidate has `evidence_complete: false` | yes |
| `CONFLICTING_OBJECTIVES` | §J.4 | yes |
| `ALL_CANDIDATES_CONSTRAINED` | eligible set is empty | yes |
| `SINGLE_CANDIDATE` | exactly one candidate in `resolve_output` | **no** — informational |

`SINGLE_CANDIDATE` deliberately does not set `detected`. With one option there is no comparison to be ambiguous about. The genuinely uncertain single-candidate case — RESOLVE found no matching rule — is already carried by `case.unresolved: true`, which WEIGH propagates; double-signalling it would just add noise.

### J.3 `supporting_signals`, defined concretely

> The number of distinct contributing agents whose payload carries **both** a non-empty `proposed_action` **and** a valid numeric `confidence` in `[0, 1]`.

Deliberately non-inferential and needs no new policy table. It counts *usable declarations*, not *risk indicators* — counting risk indicators would be a step toward scoring the entity rather than the options (§T).

Separately, `evidence_complete` is `false` on a candidate when any evidence WEIGH needed was missing (missing confidence, or a constraint that came back `INDETERMINATE`), which independently raises `INSUFFICIENT_EVIDENCE`.

### J.4 `CONFLICTING_OBJECTIVES`

Policy defines it as *"two or more weighted objectives favor opposing candidates within `near_tie_threshold` of each other."* Made deterministic:

```
Let C1, C2 be the top two eligible candidates.
CONFLICTING_OBJECTIVES ⟺
        (S(C1) − S(C2)) ≤ near_tie_threshold
    AND ∃ o : K(C1, o) > K(C2, o)
    AND ∃ p : K(C2, p) > K(C1, p)
```

The near-tie precondition matters: when totals are far apart, objectives disagreeing is normal and uninteresting. The signal detail lists which objectives pulled which way:

```python
{"code": "CONFLICTING_OBJECTIVES",
 "detail": {"favoring_top":  ["financial_exposure_prevention", "fraud_risk_reduction"],
            "favoring_next": ["merchant_trust", "operational_cost"],
            "pair": ["defer_to_agent-1", "hold_both_pending_review-2"]}}
```

This is the highest-value block in the whole output for a future bounded-Claude explanation prompt, and it is excellent demo material: *"the policy's own objectives disagree here, so a human decides."*

### J.5 The edge cases, enumerated

| Situation | WEIGH behaviour |
|---|---|
| One candidate | `SINGLE_CANDIDATE`; `top_gap: null`; `detected` unchanged by this signal alone |
| All candidates constrained | `ALL_CANDIDATES_CONSTRAINED`; `detected: true`; `ranking` still lists everything with `eligible: false`; `top_gap: null` |
| Exactly one eligible | no `NEAR_TIE` (needs two); `top_gap: null` |
| Insufficient evidence | `INSUFFICIENT_EVIDENCE`; `evidence_complete: false`; affected constraints `INDETERMINATE` ⇒ those candidates ineligible |
| No conflict at all | one `NO_CONFLICT_PROCEED` candidate; scored normally; `SINGLE_CANDIDATE`; **GOVERN must short-circuit on `case.conflict == false`** (§C.3) |
| RESOLVE unresolved | one `HOLD_BOTH_PENDING_REVIEW` candidate; `case.unresolved: true` propagated; always eligible by §I.5 |

---

## K. Policy integration

| Policy section | How WEIGH uses it |
|---|---|
| `policy.policy_id / version` | echoed into output |
| `objectives` | the canonical objective key set; drives iteration and validation |
| `weights.profiles[selected]` | the `w(o)` in §F step 3 |
| `profile_selection` | §L |
| `scoring.action_effects / strategy_effects` | the `I(c, o)` in §F step 1 |
| `scoring.confidence.min_weight` | the `α` in §H.2 |
| `hard_constraints` | ids, `enforcement`, `parameters` for §I |
| `authority` | evidence for `HC_UNAUTHORIZED_ACTION` only — reported, never enforced |
| `ambiguity` | all thresholds in §J |
| `escalation` | **not read by WEIGH.** Thresholds and outcomes are GOVERN's |
| `claude` | **not read by WEIGH.** Claude is out of scope entirely (§T.4) |
| `fallback` | **not read by WEIGH.** Fallback governs Claude/GOVERN failures |
| `audit.required_fields` | informative only; WEIGH supplies its share (§M) |

**Policy hash is computed inside WEIGH**, via `policy.loader.compute_policy_hash(policy)`, from the dict actually used. WEIGH does not accept an injected hash. This makes it structurally impossible for a caller to attach a stale hash to a set of numbers produced under different policy — the integrity guarantee is worth one SHA-256 over a small document.

WEIGH never mutates `policy`; it may `copy.deepcopy` slices it echoes into output.

---

## L. Profile selection

### L.1 Algorithm

```
for index, rule in enumerate(policy.profile_selection.rules):        # declaration order
    if all(case_context.get(k) == v for k, v in rule["when"].items()):
        return rule["profile"], reason="matched_rule", matched_rule_index=index
return policy.profile_selection.default_profile, reason="default", matched_rule_index=None
```

- **First match wins**, in file order. Deterministic and documented in the policy comment already.
- **Exact equality only** — case-sensitive, no type coercion, no truthiness, no regex, no ranges. `"when"` is inert data (the loader has a test proving code-looking strings stay strings).
- A key present in `when` but **absent** from `case_context` is a non-match.
- Extra keys in `case_context` are ignored.
- An empty `when: {}` matches everything — a legitimate catch-all; document it, do not special-case it.

### L.2 Reported as

```python
"profile": {"selected": "high_risk_merchant", "reason": "matched_rule",
            "matched_rule_index": 0,
            "matched_rule": {"when": {"merchant_risk_tier": "high"}, "profile": "high_risk_merchant"},
            "weights": {...}}
```

### L.3 Fail closed on an unknown profile

If the selected name is not a key of `weights.profiles`, raise `WeighPolicyError`. The loader validates that the three required profiles *exist* but does not validate that `profile_selection` points at real ones (§G.3 item 5) — so WEIGH must not assume it.

### L.4 The profile is an input, never an inference

Restating because it is load-bearing for §T: `merchant_risk_tier` and `merchant_trust_tier` arrive in `case_context` from merchant configuration. WEIGH must never compute them from `rto_score`, `churn_risk`, `disputed_amount`, `days_overdue`, or any other evidence field. The moment WEIGH decides *"this merchant looks high-risk"*, Sentinel has become a risk classifier.

---

## M. Audit and provenance fields

Everything a Decision Receipt needs from WEIGH (the receipt itself is out of scope):

| Receipt field | Source in WEIGH output |
|---|---|
| `policy_id` | top level |
| `policy_version` | top level |
| `policy_hash` | top level |
| `profile_selected` | `profile.selected` (+ `reason`, `matched_rule`) |
| `weights_used` | `profile.weights` |
| `objectives_considered` | keys of any candidate's `objective_impacts` |
| `candidates_considered` | `candidates[].candidate_id` |
| objective contributions | `candidates[].objective_impacts[o].contribution` (+ `raw`, `normalized`, `weight`, `source`) |
| total scores | `candidates[].total_score` |
| confidence | `evidence.case_confidence` + `candidates[].originating_confidence` |
| `hard_constraints_checked` | `constraint_evaluation.constraints_checked` |
| constraint findings | `candidates[].constraint_findings` |
| ambiguity status | `ambiguity.detected` + `ambiguity.signals` |
| provenance / source rule | `candidates[].source_rule`, `candidates[].rationale`, `evidence.agent_evidence` |
| scorer identity | `weigh_version`, `scoring_method`, `confidence_method` |

**Explicitly NOT supplied by WEIGH**, though `policy.audit.required_fields` lists them — they are GOVERN's and the orchestrator's:

`decision_id`, `timestamp`, `selected_candidate`, `outcome`, `rationale` (the *governance* rationale, distinct from RESOLVE's per-candidate rationale), `claude_invoked`, `claude_output_used`.

`weigh_version` matters more than it looks: the same policy under a different scoring implementation produces different numbers, and a receipt that records only `policy_hash` cannot explain that. Bump it on any change to the formula, the aggregation rules, or the output shape.

---

## N. Error and fallback behaviour

### N.1 One rule, uniformly applied

> **Policy gaps raise. Evidence gaps are reported.**

A policy gap means the governance system is misconfigured — continuing would produce numbers nobody can defend. An evidence gap is a normal operating condition that the output is designed to express.

### N.2 Pre-flight checks (raise `WeighPolicyError`, before any scoring)

Run all of these first, so a half-scored output never exists:

1. Every `policy.hard_constraints[].id` has a registered evaluator.
2. The selected profile exists in `weights.profiles`.
3. Every `strategy` appearing in any candidate has an entry in `scoring.strategy_effects`.
4. Every action in any candidate's `resulting_actions` has an entry in `scoring.action_effects`.
5. Every effect vector's keys equal the `objectives` key set.
6. Required policy sections/subsections are present.

Check 4 deserves comment: an unmapped action could otherwise score a neutral `0.5` and quietly win. Failing fast means a policy typo surfaces immediately and loudly — including during demo rehearsal, which is exactly when you want to find it.

### N.3 Input errors (raise `WeighInputError`)

Per §D.6. Integration bugs must never be silently governed.

### N.4 Evidence gaps (report; never raise)

| Condition | Representation |
|---|---|
| Missing/invalid agent confidence | confidence `0.0`; note `E_MISSING_CONFIDENCE`; `evidence_complete: false` |
| Constraint evidence unavailable | finding `INDETERMINATE`; candidate ineligible; `evidence_complete: false` |
| `supporting_signals` below policy minimum | `INSUFFICIENT_EVIDENCE` signal |

`notes` entries: `{"code": "E_MISSING_CONFIDENCE", "message": "...", "candidate_id": null, "agent": "rto"}`, sorted by `(code, agent, candidate_id)`.

### N.5 What WEIGH never does on error

No default score. No default profile substitution when one was explicitly selected but invalid. No dropping an unscoreable candidate. No emitting a partial result that looks complete. `policy.fallback` (`HOLD_FOR_REVIEW` / `ESCALATE`) applies to Claude and GOVERN failure modes and is **not** WEIGH's to apply — WEIGH raises, and the orchestrator applies the conservative fallback.

---

## O. Determinism requirements

Purity contract: **same four inputs ⇒ byte-identical output.**

| Requirement | Implementation rule |
|---|---|
| No clock | Never call `datetime.now()` / `utcnow()` / `time.time()`. WEIGH output contains **no timestamp**. Agent timestamps are not copied through (§E.2) |
| No randomness | No `random`, no `uuid`, no `hash()` of unordered collections. Never generate a `case_id` |
| No I/O | No `open`, no DB session, no network, no Claude client. Policy arrives as an argument |
| No global state | No module-level mutable caches. No `os.environ` reads |
| Stable ordering | Objective keys sorted alphabetically; `contributing_agents`, `constraints_checked`, id lists, `signals` sorted; `candidates` in RESOLVE's original order; `ranking` by the §E.4 total order |
| No set leakage | Sets are internal only; anything emitted is a sorted list |
| Stable numbers | Rounding fixed at 4 dp per §F.1; policy values authored at ≤2 dp |
| No mutation | Never mutate `resolve_output`, `agent_actions`, `case_context`, or `policy` |
| No dynamic execution | No `eval` / `exec` / `getattr` dispatch on policy strings. Evaluator lookup is an explicit dict keyed by constraint id |

---

## P. Test strategy

Colocated `test_*.py` in `backend/weigh/`, matching the existing house style (`resolve/test_resolver.py`, `policy/test_loader.py`). Runs under the existing `pytest.ini` (`pythonpath = backend`, `testpaths = backend`).

Every test uses literal fixture dicts. No DB, no network, no Claude, no clock, no randomness. Policy variations use `copy.deepcopy(load_policy())` mutated in memory — mirroring `test_loader.py`'s `_raw_policy_dict()` / `_write_policy()` pattern.

### P.1 Minimum high-value matrix

| # | Test | Asserts |
|---|---|---|
| 1 | `test_no_conflict_single_candidate` | one candidate scored; `SINGLE_CANDIDATE`; `case.conflict is False`; `top_gap is None` |
| 2 | `test_single_candidate_unresolved_path` | `case.unresolved is True` propagated; the `HOLD_BOTH` candidate is eligible (§I.5) |
| 3 | `test_multiple_candidates_all_scored` | every input candidate appears with `objective_impacts` for all five objectives |
| 4 | `test_known_conflict_end_to_end` | §Q numbers reproduced exactly: `0.7500` / `0.6200` |
| 5 | `test_hard_constraint_marks_candidate_ineligible` | `VIOLATED`; `eligible is False`; `eligibility_basis` names the constraint |
| 6 | `test_high_score_does_not_defeat_hard_constraint` | §S: blocked candidate has `score_rank == 1` **and** is last in `ranking`; `ranking[0].eligible is True` |
| 7 | `test_near_tie_detected` | gap inside threshold ⇒ `NEAR_TIE`, group membership, `tie_group` set |
| 8 | `test_near_tie_boundary_is_inclusive` | gap exactly `== near_tie_threshold` ⇒ tie |
| 9 | `test_clear_winner_no_ambiguity` | gap outside threshold ⇒ `detected is False`, `signals == []` |
| 10 | `test_low_confidence_signal` | `case_confidence 0.5375 < 0.55` ⇒ `LOW_CONFIDENCE` |
| 11 | `test_missing_confidence_is_conservative` | missing ⇒ `0.0`, note emitted, `evidence_complete False`, acting candidate ineligible via `HC_CONFIDENCE_FLOOR` |
| 12 | `test_insufficient_evidence_signal` | `supporting_signals` below policy minimum ⇒ signal |
| 13 | `test_indeterminate_constraint_blocks_but_is_not_violated` | status `INDETERMINATE`, ineligible, **not** in `violated_candidate_ids` |
| 14 | `test_all_candidates_constrained` | eligible set empty ⇒ signal, `detected True`, all candidates still listed |
| 15 | `test_profile_selection_first_match_wins` | `merchant_risk_tier: high` + `merchant_trust_tier: trusted` ⇒ `high_risk_merchant` (rule 0) |
| 16 | `test_profile_selection_falls_back_to_default` | empty context ⇒ `standard`, `reason == "default"` |
| 17 | `test_policy_profile_change_changes_result` | §R: identical inputs, mutated weights ⇒ different ranking; `policy_hash` differs |
| 18 | `test_policy_threshold_change_changes_ambiguity` | §R variant A: only `near_tie_threshold` changed ⇒ `detected` flips |
| 19 | `test_deterministic_repeated_calls` | `out1 == out2` **and** `json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True)` |
| 20 | `test_no_final_decision_field` | recursive walk asserts no §E.6 key at any depth |
| 21 | `test_no_candidate_invention` | candidate id set equals RESOLVE's; `strategy` / `preferred_agent` / `resulting_actions` / `rationale` / `source_rule` byte-identical |
| 22 | `test_contributions_sum_to_total` | `round(sum(contributions), 4) == total_score` exactly, per §F.1 |
| 23 | `test_scores_within_unit_interval` | `0.0 <= total_score <= 1.0`; `0.0 <= normalized <= 1.0` |
| 24 | `test_policy_hash_matches_policy_used` | output hash `== compute_policy_hash(policy_passed_in)` |
| 25 | `test_unmapped_action_raises_policy_error` | effect entry deleted ⇒ `WeighPolicyError`, no partial output |
| 26 | `test_unregistered_constraint_raises_policy_error` | new constraint id in policy ⇒ `WeighPolicyError` |
| 27 | `test_unknown_profile_raises_policy_error` | rule points at a nonexistent profile ⇒ `WeighPolicyError` |
| 28 | `test_missing_agent_payload_raises_input_error` | `agent_b` absent from `agent_actions` ⇒ `WeighInputError` |
| 29 | `test_duplicate_candidate_ids_raise_input_error` | ⇒ `WeighInputError` |
| 30 | `test_inputs_are_not_mutated` | deepcopy-compare all four arguments before/after |
| 31 | `test_confidence_blend_formula` | `{0.40, 0.95}`, α`=0.5` ⇒ `0.5375`; α`=1.0` ⇒ `0.40`; α`=0.0` ⇒ `0.675`; single agent ⇒ identity |
| 32 | `test_agent_order_does_not_change_result` | swapping `agent_a`/`agent_b` roles yields the same scores |
| 33 | `test_no_clock_or_randomness` | `monkeypatch` `datetime.datetime`, `time.time`, `random.random` to raise; call succeeds (mirrors `test_no_eval_or_dynamic_execution`) |
| 34 | `test_no_eval_or_dynamic_execution` | `monkeypatch` `builtins.eval` / `exec` to raise; a policy carrying code-looking strings is treated as inert data |
| 35 | `test_thirdwatch_threshold_mirrors_rto_agent_band` | §I.8: any policy `high_risk_rto_score` parameter equals `rto.py`'s published cutoff |
| 36 | `test_output_ordering_is_canonical` | objective keys sorted; agent/constraint/signal lists sorted |

### P.2 Fixture guidance

Build a `_case()` helper returning the four inputs so each test mutates one thing. Do **not** call the mock agents for scoring tests — their confidences are hardcoded at 0.80–0.95, so `HC_CONFIDENCE_FLOOR` and `LOW_CONFIDENCE` are unreachable through them. Use literal payloads with injected confidences for those paths.

---

## Q. Worked example — end-to-end, two candidates

**Case:** Payouts vs Dispute on `order_vendor`. Profile: `standard`.

**Agent evidence**

```python
payouts = {"agent": "payouts", "proposed_action": "RELEASE_PAYMENT",      "confidence": 0.95, "amount": 42000, "days_overdue": 9}
dispute = {"agent": "dispute", "proposed_action": "HOLD_RELATED_ACTIONS", "confidence": 0.95, "dispute_status": "OPEN", "disputed_amount": 42000}
case_context = {"case_id": "case-Q", "merchant_id": "mrch_001"}      # no tier ⇒ default profile
```

Conflict Matrix: `RELEASE_PAYMENT` × `HOLD_RELATED_ACTIONS` on `order_vendor` ⇒ conflict.
RESOLVE (`release_payment_vs_hold_related_actions`, `dispute` outranks `payouts`):

- `C1 = defer_to_agent-1` — `DEFER_TO_AGENT`, preferred `dispute`, actions `["HOLD_RELATED_ACTIONS"]`
- `C2 = hold_both_pending_review-2` — `HOLD_BOTH_PENDING_REVIEW`, actions `[]`

**Profile:** no `when` matches ⇒ `standard` = `{fep 0.30, frr 0.25, crr 0.20, mt 0.15, oc 0.10}`, `reason: "default"`.

**Q.1 — C1** (one action ⇒ min is trivially `HOLD_RELATED_ACTIONS`)

| Objective | raw | normalized | weight | contribution |
|---|---|---|---|---|
| compliance_risk_reduction | +0.60 | 0.80 | 0.20 | **0.1600** |
| financial_exposure_prevention | +0.90 | 0.95 | 0.30 | **0.2850** |
| fraud_risk_reduction | +0.70 | 0.85 | 0.25 | **0.2125** |
| merchant_trust | −0.30 | 0.35 | 0.15 | **0.0525** |
| operational_cost | −0.20 | 0.40 | 0.10 | **0.0400** |
| | | | | **total = 0.7500** |

**Q.2 — C2** (no actions ⇒ strategy vector `HOLD_BOTH_PENDING_REVIEW`)

| Objective | raw | normalized | weight | contribution |
|---|---|---|---|---|
| compliance_risk_reduction | +0.50 | 0.75 | 0.20 | **0.1500** |
| financial_exposure_prevention | +0.60 | 0.80 | 0.30 | **0.2400** |
| fraud_risk_reduction | +0.50 | 0.75 | 0.25 | **0.1875** |
| merchant_trust | −0.50 | 0.25 | 0.15 | **0.0375** |
| operational_cost | −0.90 | 0.05 | 0.10 | **0.0050** |
| | | | | **total = 0.6200** |

**Q.3 — the rest**

- Confidence: `C_min = 0.95`, `C_mean = 0.95` ⇒ `case_confidence = 0.9500`. `originating_confidence`: C1 → `dispute` 0.95; C2 → no preferred agent ⇒ 0.95. `supporting_signals = 2`.
- Constraints:
  - `HC_PAYOUT_DURING_CHARGEBACK` — neither candidate contains `RELEASE_PAYMENT` ⇒ `NOT_APPLICABLE` for both. *(The dispute status is `OPEN`; the constraint would fire on a release candidate, which RESOLVE did not produce here. This is the layering working: RESOLVE already declined to propose the unsafe option, and WEIGH confirms rather than assumes.)*
  - `HC_THIRDWATCH_HIGH_RISK_PAYOUT` — no `RELEASE_PAYMENT` ⇒ `NOT_APPLICABLE`.
  - `HC_RETENTION_TO_FLAGGED_MERCHANT` — no `WIN_BACK_OFFER` ⇒ `NOT_APPLICABLE`.
  - `HC_CONFIDENCE_FLOOR` — C1: `0.95 ≥ 0.60` ⇒ `SATISFIED`. C2: no actions ⇒ `NOT_APPLICABLE` (§I.5).
  - `HC_UNAUTHORIZED_ACTION` — C1: `HOLD_RELATED_ACTIONS ∈ dispute.autonomous_actions`, `max_autonomous_amount: null` ⇒ `SATISFIED`. C2: `NOT_APPLICABLE`.
  - Both eligible.
- Ranking: `[{C1, rank 1, score_rank 1, 0.7500, eligible}, {C2, rank 2, score_rank 2, 0.6200, eligible}]`.
- Ambiguity: `top_gap = 0.1300 > 0.05` ⇒ no `NEAR_TIE`. `0.9500 ≥ 0.55` ⇒ no `LOW_CONFIDENCE`. `2 ≥ 1` ⇒ no `INSUFFICIENT_EVIDENCE`. C1 beats C2 on every objective ⇒ no `CONFLICTING_OBJECTIVES`. **`detected: false`.**

WEIGH stops here. It has **not** said "hold the payment." It has said: *under `standard`, deferring to the dispute agent scores 0.7500, holding both scores 0.6200, the gap is decisive, confidence is 0.95, and nothing is constrained.* GOVERN decides.

**Q.4 — the no-conflict contrast** (why §C.3 exists)

Same agents, but `dispute_status: "CLOSED"` ⇒ `CLOSE_CASE` ⇒ no conflict ⇒ one candidate `NO_CONFLICT_PROCEED` with `resulting_actions: ["RELEASE_PAYMENT", "CLOSE_CASE"]`. Element-wise minimum:

| Objective | min(RELEASE_PAYMENT, CLOSE_CASE) | normalized | weight | contribution |
|---|---|---|---|---|
| compliance_risk_reduction | min(−0.30, +0.30) = −0.30 | 0.35 | 0.20 | 0.0700 |
| financial_exposure_prevention | min(−0.80, +0.10) = −0.80 | 0.10 | 0.30 | 0.0300 |
| fraud_risk_reduction | min(−0.60, 0.00) = −0.60 | 0.20 | 0.25 | 0.0500 |
| merchant_trust | min(+0.70, +0.20) = +0.20 | 0.60 | 0.15 | 0.0900 |
| operational_cost | min(+0.50, +0.40) = +0.40 | 0.70 | 0.10 | 0.0700 |
| | | | | **total = 0.3100** |

`0.3100 ≤ hold_max_score (0.40)`. A naive GOVERN would **hold a case in which no agent disagreed with anything**. The score is low because `RELEASE_PAYMENT` is intrinsically negative on financial exposure — correct as a comparative statement, meaningless as an absolute verdict when there is no alternative to compare against. Hence §C.3: **GOVERN short-circuits `conflict == false`.** Catching this before implementation is precisely what this document is for.

---

## R. Worked example — a policy change changes the result

Both variants change **only `policy_bundle.yaml`**. Zero application code changes. `policy_hash` visibly changes in the receipt, which is the proof that the behaviour came from policy.

### R.1 Variant A — one line, works with RESOLVE exactly as it is today

Same case as §Q (scores `0.7500` / `0.6200`, gap `0.1300`).

```yaml
ambiguity:
  near_tie_threshold: 0.05     # →  0.15
```

| | before | after |
|---|---|---|
| C1 / C2 scores | 0.7500 / 0.6200 | **identical** |
| `top_gap` | 0.1300 | 0.1300 |
| `near_tie_threshold` | 0.05 | 0.15 |
| `NEAR_TIE` | no | **yes** |
| `ambiguity.detected` | `false` | **`true`** |
| `tie_group` | `null`, `null` | `1`, `1` |
| downstream | GOVERN proceeds on a clear winner | GOVERN sees ambiguity → escalation path |

Same agents, same evidence, same code, same scores. One number in a YAML file, and the case changes from *autonomously governable* to *needs a human*. The gap is deliberately exaggerated for stage legibility.

### R.2 Variant B — full ranking reversal (requires the §C.4 RESOLVE addendum)

**Case:** RTO vs Retention on `customer`. `HOLD_ORDER` × `WIN_BACK_OFFER` ⇒ conflict, rule `hold_order_vs_win_back_offer`. With `defer_to_agent-2` present, three candidates:

- `defer_to_agent-1` → `["HOLD_ORDER"]` (rto preferred by priority)
- `defer_to_agent-2` → `["WIN_BACK_OFFER"]` (the counterfactual)
- `hold_both_pending_review-2` → `[]`

**Before — `standard` weights** `{fep .30, frr .25, crr .20, mt .15, oc .10}`

| Candidate | crr | fep | frr | mt | oc | **total** |
|---|---|---|---|---|---|---|
| `defer_to_agent-1` (HOLD_ORDER) | .20×.60=.1200 | .30×.85=.2550 | .25×.80=.2000 | .15×.10=.0150 | .10×.40=.0400 | **0.6300** |
| `hold_both_pending_review-2` | .20×.75=.1500 | .30×.80=.2400 | .25×.75=.1875 | .15×.25=.0375 | .10×.05=.0050 | **0.6200** |
| `defer_to_agent-2` (WIN_BACK_OFFER) | .20×.40=.0800 | .30×.35=.1050 | .25×.30=.0750 | .15×.95=.1425 | .10×.65=.0650 | **0.4675** |

Ranking: **hold_order → hold_both → win_back**. `top_gap = 0.0100 ≤ 0.05` ⇒ `NEAR_TIE` between the top two.

**The policy edit** — the merchant-trust objective is made dominant in the `standard` profile (i.e. `standard` is re-weighted to the `trusted_merchant` values). `case_context` is untouched, so no input changes:

```yaml
weights:
  profiles:
    standard:
      financial_exposure_prevention: 0.30   # → 0.25
      fraud_risk_reduction:          0.25   # → 0.15
      compliance_risk_reduction:     0.20   # → 0.15
      merchant_trust:                0.15   # → 0.35
      operational_cost:              0.10   #   unchanged
```

**After** `{fep .25, frr .15, crr .15, mt .35, oc .10}`

| Candidate | crr | fep | frr | mt | oc | **total** |
|---|---|---|---|---|---|---|
| `defer_to_agent-2` (WIN_BACK_OFFER) | .15×.40=.0600 | .25×.35=.0875 | .15×.30=.0450 | .35×.95=.3325 | .10×.65=.0650 | **0.5900** |
| `hold_both_pending_review-2` | .15×.75=.1125 | .25×.80=.2000 | .15×.75=.1125 | .35×.25=.0875 | .10×.05=.0050 | **0.5175** |
| `defer_to_agent-1` (HOLD_ORDER) | .15×.60=.0900 | .25×.85=.2125 | .15×.80=.1200 | .35×.10=.0350 | .10×.40=.0400 | **0.4975** |

Ranking: **win_back → hold_both → hold_order** — a complete reversal. `top_gap = 0.0725 > 0.05` ⇒ `NEAR_TIE` **disappears**; a genuine winner emerges where there was ambiguity.

### R.3 The flip algebra, so the team can tune this on purpose

For any two candidates, the gap is linear in the weights:

```
gap(w) = Σ_o  w(o) · [ N(C1, o) − N(C2, o) ]
```

For `HOLD_ORDER` vs `WIN_BACK_OFFER`, `Δ = (fep +0.50, frr +0.50, crr +0.20, mt −0.85, oc −0.25)`:

- `standard`: `.30(.50) + .25(.50) + .20(.20) + .15(−.85) + .10(−.25) = +0.1625` ⇒ hold wins
- re-weighted: `.25(.50) + .15(.50) + .15(.20) + .35(−.85) + .10(−.25) = −0.0925` ⇒ win-back wins

So `WIN_BACK_OFFER` overtakes `HOLD_ORDER` exactly when

```
w(mt)  >  [ 0.50·w(fep) + 0.50·w(frr) + 0.20·w(crr) − 0.25·w(oc) ] / 0.85
```

Use this to pick demo values deliberately rather than by trial and error.

### R.4 Honest statement of the dependency

**Variant A works today.** **Variant B needs `defer_to_agent-2`** from §C.4. Without it the only two candidates are "hold the order" and "hold everything", which sit on the same side of the risk/trust trade-off and therefore never reorder under any weight profile — the profile changes the scores but not the ranking. If the team declines the RESOLVE addendum, Variant A is the demo, and the claim to make on stage is *"policy changes the governance outcome"* rather than *"policy changes the ranking."*

---

## S. Worked example — a hard constraint defeating a high score

**Case:** the §R.2 setup, under the re-weighted (trust-dominant) profile, with one added governance fact:

```python
case_context = {"case_id": "case-S", "merchant_id": "mrch_009",
                "merchant_flags": ["FRAUD_REVIEW"]}
```

Scores are unchanged from §R.2 — the constraint does not touch the arithmetic:

| Candidate | total_score | score_rank |
|---|---|---|
| `defer_to_agent-2` (WIN_BACK_OFFER) | **0.5900** | **1** |
| `hold_both_pending_review-2` | 0.5175 | 2 |
| `defer_to_agent-1` (HOLD_ORDER) | 0.4975 | 3 |

**Constraint findings on the top scorer:**

```python
{"constraint_id": "HC_RETENTION_TO_FLAGGED_MERCHANT",
 "status": "VIOLATED",
 "enforcement": "block",
 "predicate": "'WIN_BACK_OFFER' in candidate.resulting_actions AND case_context.merchant_flags ∩ {FRAUD_REVIEW, COMPLIANCE_REVIEW} ≠ ∅",
 "observed": {"resulting_actions": ["WIN_BACK_OFFER"], "case_context.merchant_flags": ["FRAUD_REVIEW"]},
 "source": "policy.hard_constraints[2]",
 "advisory": true}
```

⇒ `eligible: false`, `eligibility_basis: "blocked_by:HC_RETENTION_TO_FLAGGED_MERCHANT"`.

**Resulting `ranking`** (eligible first, then score, §E.4):

| rank | candidate | total_score | score_rank | eligible |
|---|---|---|---|---|
| 1 | `hold_both_pending_review-2` | 0.5175 | 2 | true |
| 2 | `defer_to_agent-1` | 0.4975 | 3 | true |
| 3 | `defer_to_agent-2` | **0.5900** | **1** | **false** |

Ambiguity: eligible `top_gap = 0.0200 ≤ 0.05` ⇒ `NEAR_TIE` between the two survivors, plus `constraint_evaluation.violated_candidate_ids: ["defer_to_agent-2"]`. WEIGH reports both, honestly, and decides neither.

**What this demonstrates:**

1. The highest-scoring option is **not** at the top of `ranking` — score cannot climb over a constraint, structurally, not by convention.
2. `score_rank: 1` is preserved, so the receipt can state plainly: *"the win-back offer scored best at 0.5900 and was blocked by HC_RETENTION_TO_FLAGGED_MERCHANT."* Suppression is visible, not silent.
3. `ranking[0]` is eligible, so even a careless GOVERN cannot pick the blocked option — **and GOVERN still re-evaluates the constraint itself**, from `policy` and `agent_actions`, because `advisory: true` says WEIGH's finding is evidence, not enforcement.
4. Two independent layers must both fail before an unsafe action escapes.

---

## T. Razorpay Open Track differentiation check

### T.1 The question, answered architecturally

> *Why is this WEIGH layer part of a multi-agent governance product rather than an AI Risk Manager?*

**Because of what it takes as input and what it scores.**

A risk manager takes **entity evidence** and produces a **judgment about that entity**: this order is risky, this merchant is fraudulent, this customer will churn. Its input is raw signal; its output is a risk estimate; it works on a single entity in isolation.

WEIGH takes **an already-generated set of candidate resolutions to a detected inter-agent disagreement** and produces **a comparison of those options under a declared policy**. Its input is other agents' *already-formed conclusions*; its output ranks *governance options*, not entities.

The decisive structural test: **remove the disagreement and WEIGH has nothing to do.** With one agent, or with two agents that agree, there are no competing candidates, so there is nothing to weigh. A risk manager is entirely unaffected by how many agents exist — it scores the entity either way. Sentinel's WEIGH layer *cannot exist* outside a multi-agent setting. That is not positioning; it is a property of its type signature.

Two corollaries in the code:

- **WEIGH never estimates risk.** No function in this design maps evidence → a risk quantity. `rto_score`, `churn_risk`, `disputed_amount`, `days_overdue` are **never read into the scoring arithmetic**. Risk estimation belongs entirely to the agents; §I.8 makes it a rule that WEIGH defers to the agent's own published verdict rather than re-deriving a band.
- **WEIGH's scoring inputs are policy text, not data.** Every number in `S(c)` comes from either `weights.profiles` or `scoring.*_effects` — both authored governance stances (§G.2). None is learned, fitted, or inferred. Change the policy file and the answer changes; change the merchant's transaction history and the *scores* do not move at all.

### T.2 The three permitted evidence channels

Evidence enters WEIGH through exactly three narrow, non-inferential channels, and **never as a continuous magnitude in the score arithmetic**:

| # | Channel | Form | Enters the score? |
|---|---|---|---|
| 1 | **Confidence** — a scalar the agent itself declared | `[0,1]` float, aggregated but never recomputed (§H) | **No.** Reported alongside; acts as a gate |
| 2 | **Constraint predicates** — declarative fact checks (`dispute_status == "OPEN"`, `WIN_BACK_OFFER ∈ actions`) | boolean | **No.** Produces eligibility, never points |
| 3 | **Authority facts** — action ∈ `autonomous_actions`, amount vs `max_autonomous_amount` | boolean | **No.** Advisory finding only |

This is the bright line. Anything that would need a fourth channel — "read this number and turn it into a score" — is a design change requiring explicit review, because it is the first step toward becoming a risk engine.

### T.3 Functionality considered and rejected

Each of these was on the table and is **removed from the design**:

| Rejected | Why it was tempting | Why it is out |
|---|---|---|
| Deriving objective scores from evidence, e.g. `fraud_risk_reduction = f(rto_score, disputed_amount)` | Feels "smarter"; makes scores responsive to the case | This *is* a fraud/risk model. It would duplicate the agents' job, and the model would silently diverge from them. **Replaced by** policy-declared effect vectors (§G) |
| Inferring `merchant_risk_tier` from evidence when `case_context` omits it | Convenient; avoids a required input | Inferring a merchant risk tier is literally risk classification. **Replaced by** an explicit `case_context` fact, defaulting to `standard` (§L.4) |
| Re-deriving the RTO high-risk band from `rto_score` inside `HC_THIRDWATCH_HIGH_RISK_PAYOUT` | The constraint needs a boolean; the score is right there | Creates a second risk classifier that can disagree with the agent owning the question. **Replaced by** deferring to the agent's published verdict, with a mirror-consistency test (§I.8, P.35) |
| Confidence-weighted scores (`S × confidence`) | Intuitive, common in scoring systems | Conflates option quality with evidential certainty and breaks GOVERN's separate confidence gates. **Replaced by** orthogonal reporting (§H.4) |
| A "risk_score" / "severity" / "exposure_amount" field in output | Useful for a dashboard | Introduces an entity-level risk quantity, which is the product boundary. Money amounts appear **only** inside authority findings as a boolean comparison |
| Tuning effect values against observed outcomes | Would make scores "better calibrated" | Calibration against outcomes is model training. These are governance stances, deliberately hand-authored, and carry the policy bundle's demo disclaimer |

### T.4 The Claude boundary

Claude is **not part of WEIGH**, in any form: no client, no import, no prompt construction, no optional path, no `claude` policy section read. WEIGH is deterministic arithmetic over policy data, and `test_no_clock_or_randomness` plus the absent import make that verifiable rather than promised.

What WEIGH *does* is hand GOVERN enough structure for a future **bounded** invocation, if and only if policy permits it (`claude.invocation_conditions`: case is ambiguous **and** no hard constraint violated):

- exact objective contributions per candidate — so an explanation can cite arithmetic instead of speculating;
- `CONFLICTING_OBJECTIVES.detail` naming which objectives pulled which way — the substance of any "why is this hard?" explanation;
- constraint findings with `status` and `observed` — so an explanation can state what was checked and what was missing;
- `case_confidence` with its inputs — so uncertainty can be described rather than guessed.

The policy invariants (`may_invent_candidates: false`, `may_bypass_hard_constraints: false`, `may_override_authority: false`, `may_directly_execute_actions: false`, all enforced by `loader._validate_claude`) remain GOVERN's to honour. WEIGH's contribution to that safety is structural: the candidate set is closed **before** any model is ever consulted, so there is no point in the pipeline where a model could add an option.

### T.5 Verdict

The design is clear of the adjacent tracks. It is not a fraud detector (it never classifies fraud), not a chargeback detector (it consumes the dispute agent's status as a fact), not an RTO scorer (§I.8 forbids re-deriving the band), not a retention optimizer (retention is one input among several, and its preferred action is routinely ranked below holds), and not a payment risk engine (no risk quantity exists anywhere in the output).

The one thing WEIGH does that none of those products does: **it reconciles conflicting recommendations from independent agents against a versioned, hashable, externally-editable governance policy, and shows its work.**

---

## U. Recommended implementation file structure

### U.1 New package

Colocated tests, matching the existing house convention.

```
backend/weigh/
    __init__.py            # exports evaluate_candidates, WeighInputError, WeighPolicyError
    weigh.py               # public entry point; orchestrates the phases below; owns output assembly
    profile.py             # select_profile(case_context, policy) -> (name, reason, index, rule, weights)
    scoring.py             # impact vector selection, normalization, weighting, totals, ranking
    confidence.py          # min_blend_v1: case_confidence + originating_confidence
    constraints.py         # CONSTRAINT_EVALUATORS registry + the five advisory evaluators
    ambiguity.py           # the six signals
    errors.py              # WeighInputError, WeighPolicyError
    schema.py              # output key constants, FORBIDDEN_OUTPUT_KEYS, WEIGH_VERSION

    test_weigh.py          # end-to-end (§Q), contract invariants, structural guards (tests 1-6, 19-24, 28-30, 32-33, 36)
    test_scoring.py        # formula, normalization, rounding, ranking order, tie handling (22, 23, 25)
    test_confidence.py     # blend formula, missing confidence, alpha extremes (10, 11, 31)
    test_constraints.py    # five evaluators, four statuses, no-action invariant (5, 13, 26, 35)
    test_ambiguity.py      # six signals, boundaries, edge cases (7, 8, 9, 12, 14)
    test_profile.py        # first-match, default, unknown profile (15, 16, 27)
    test_policy_sensitivity.py  # §R variants A and B (17, 18)
```

**Phase order for implementation:** `errors.py` → `schema.py` → `profile.py` → `scoring.py` → `confidence.py` → `constraints.py` → `ambiguity.py` → `weigh.py`. Each with its tests before moving on. `weigh.py` is assembly only — no arithmetic of its own.

### U.2 Changes to existing files

| File | Change | Approval needed |
|---|---|---|
| `backend/policy/policy_bundle.yaml` | add `scoring:` section (§G.1); bump `policy.version` → `1.1.0` | **Yes** — deferred out of this task per instruction |
| `backend/policy/policy_schema.json` | add `scoring` to `properties` **and** `required` | **Yes** |
| `backend/policy/loader.py` | add `_validate_scoring()`; recommended: validate `profile_selection` profile names exist (§G.3.5) | **Yes** |
| `backend/resolve/resolver.py` | **optional** additive `defer_to_agent-2` candidate (§C.4) — required only for demo variant B | **Yes — explicit decision required** |
| `backend/main.py` | none in this phase | — |

### U.3 Explicitly out of scope

GOVERN, the Action Executor, the Decision Receipt, Claude integration, HMAC policy signing, database persistence, API endpoints, and pipeline orchestration wiring. WEIGH is a pure function; whoever calls it owns the plumbing.

---

## Decision log — what an implementer must not re-litigate

| # | Decision | Section |
|---|---|---|
| 1 | Element-wise **minimum** over resulting actions; strategy vector only when there are no actions | F |
| 2 | Normalization `(raw+1)/2`; all objectives higher-is-better, including `operational_cost` | F, G |
| 3 | Contributions rounded to 4 dp **first**; total is the sum of rounded contributions | F.1 |
| 4 | Confidence is `α·min + (1−α)·mean`; the brief's "mean floored by min" is degenerate | H.1, H.2 |
| 5 | Confidence never multiplies the score and never breaks a tie | H.4, E.4 |
| 6 | Two confidences: `case_confidence` and per-candidate `originating_confidence` | H.3 |
| 7 | `INDETERMINATE` blocks but is never reported as `SATISFIED` | I.3 |
| 8 | No action ⇒ no constraint violation; guarantees a non-empty eligible set when a HOLD candidate exists | I.5 |
| 9 | Constraint logic in a code registry, thresholds in policy; missing evaluator raises | I.6 |
| 10 | Ranking sorts eligible-first, so `ranking[0]` is never blocked; `score_rank` preserves the score story | E.4 |
| 11 | Near-tie is an **absolute** gap, inclusive `≤`; no relative mode | J.1 |
| 12 | `ambiguity.detected`, never a status naming an escalation outcome | E.5 |
| 13 | Profile comes from `case_context`, never inferred from evidence | L.4 |
| 14 | Policy gaps raise; evidence gaps are reported | N.1 |
| 15 | `policy_hash` computed inside WEIGH from the policy actually used | K |
| 16 | No timestamp anywhere in WEIGH output | E.2, O |
| 17 | Evidence enters only via confidence, boolean predicates, and authority facts | T.2 |

---

**End of design. Nothing in `backend/` was created or modified for this task.**
