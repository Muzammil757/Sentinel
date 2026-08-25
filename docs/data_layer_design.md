# Sentinel — Data Layer Design (Supabase / PostgreSQL)

**Status:** Design only. Nothing in `backend/` was created or modified for this task. No migrations, no SQL, no SDKs.
**Phase:** 3A (follows EXECUTOR, commit `5729314`)
**Audience:** the engineer implementing the persistence adapter and, later, the API layer.
**Rule for the implementer:** every architectural decision needed to build this layer is fixed below. If you hit a decision this document does not answer, stop and escalate rather than inventing one.

---

## A. Purpose and scope

The data layer's job is **persistence, auditability, and a UI read model** for a pipeline that is already fully deterministic and fully decided by the time anything reaches the database. It is explicitly **not**:

- a decision-making layer (no scoring, no ranking, no authorization logic in SQL),
- a second copy of policy (policy stays in `backend/policy/policy_bundle.yaml`, loaded by Python),
- a queue, cache, or orchestration mechanism.

Everything Postgres stores here is something the Python backend already computed and handed over as a plain dict. The database's only questions are: *where does this go, how do I find it again, and can I prove nothing was altered after the fact.*

Scope of this document: table-by-table schema, relationships, JSONB decisions, idempotency/re-run strategy, indexes, RLS direction, and how the future UI and audit trail read from it. It does **not** cover: the Python repository/adapter code that will write these rows, FastAPI route shapes, or the Supabase project setup itself.

---

## B. Current pipeline grounding

Read directly from the code at `5729314`, not assumed:

```
mock_agents/{payouts,disputes,rto,retention}.py
        │  agent payload: {agent, <domain fields>, proposed_action, confidence, timestamp}
        ▼
conflict_matrix/integration.py  evaluate_agent_actions(a, b, entity_type)
        │  conflict_result: {agent_a, agent_b, action_a, action_b, entity_type, conflict, reason}
        ▼
resolve/resolver.py  generate_resolution_candidates(conflict_result, a_detail, b_detail)
        │  resolve_output: {entity_type, agent_a, agent_b, conflict, unresolved,
        │                    candidates: [{candidate_id, strategy, preferred_agent,
        │                                  resulting_actions, rationale, source_rule}]}
        ▼
weigh.evaluate_candidates(resolve_output, agent_actions, case_context, policy)
        │  weigh_output (docs/weigh_layer_design.md §E) — adds objective_impacts,
        │  total_score, ranking, ambiguity, constraint_evaluation to each candidate
        ▼
govern.decide(weigh_output, agent_actions, case_context, policy, advisor=None)
        │  govern_output (docs/govern_layer_design.md §E) — names exactly one
        │  outcome ∈ {PROCEED, HOLD, ESCALATE, AMBIGUOUS}, computes execution_authorized
        ▼
executor.execute(govern_output, request=None)
        │  execution receipt — EXECUTED or REJECTED, every fact traced back to GOVERN
        ▼
   [ DATA LAYER — this document ]
        ▼
       API
        ▼
     Web UI
```

Two things verified directly in code, because they change the schema:

1. **`profile.profile_name`, not `profile.selected`.** `weigh_layer_design.md`'s own worked example uses `"selected"`, but `weigh/schema.py` lists `"selected"` in `FORBIDDEN_OUTPUT_KEYS`, and `weigh/profile.py` emits `"profile_name"`. `govern_layer_design.md` §0 documents this exact trap. This document uses `profile_name` throughout — the design docs are aspirational where they conflict with the code; the code is truth.
2. **The pipeline today is strictly pairwise.** `conflict_matrix.integration.evaluate_agent_actions` takes exactly two agent payloads (`action_a`, `action_b`); RESOLVE and WEIGH consume exactly one conflict per run. `govern/conftest.py`'s `no_conflict_release_case` shows a third agent (`rto`) can additionally ride along in `agent_actions` as evidence for a constraint check, without being a party to the conflict itself. The schema below reflects this: one `conflicts` row per run, `agent_outputs` rows tagged by role.

No frontend and no Supabase/Postgres code exist anywhere in the repository today. The only persistence in the repo is `backend/database/` — a SQLite/SQLAlchemy scaffold — addressed in §Q.

---

## C. Data ownership boundaries

| Concern | Owner | Data layer's role |
|---|---|---|
| Conflict detection, candidate generation, scoring, constraints, authorization, execution | Python (`resolve`, `weigh`, `govern`, `executor`) | **None.** Never re-derives, never re-checks, never re-scores. |
| Policy content and identity (`policy_id`, `policy_version`, `policy_hash`) | `backend/policy/` | Stores the identity that traveled with a run; never edits or re-hashes it. |
| Storage, retrieval, audit-trail assembly | Supabase/Postgres | Full ownership. |
| Read-optimized shape for the Web UI | Supabase/Postgres (read model) | Denormalizes only what §M requires, never invents a new fact. |

This mirrors the WEIGH/GOVERN boundary already established in the codebase (`weigh_output.constraint_evaluation.authority == "advisory_only"`, GOVERN's `"enforcing"` counterpart): the database is **advisory storage**, never an enforcement point. No RLS policy in this design may gate *whether an action executes* — only *who may read or write which rows*.

---

## D. Case / run identity

Section G of the task brief asks explicitly for this distinction, and the grounding in §B forces it:

| Identity | What it names | Where it comes from |
|---|---|---|
| **Case identity** | The real-world situation being adjudicated (a dispute, an order, a customer) | `case_context.case_id`, which WEIGH's own contract says is **optional, echoed if present, never generated** (`weigh_layer_design.md` §D.4) |
| **Run identity** | One execution of the pipeline against that case | Does not exist as a concept in the Python backend at all — every layer is a pure function call. The data layer must invent it. |
| **Decision identity** | GOVERN's `decision_id` — a SHA-256 content hash of `{govern_version, policy_hash, case_context, weigh_output}` (`govern_layer_design.md` §P.2) | Computed inside GOVERN, before any advisor runs |
| **Receipt identity** | EXECUTOR's `receipt_id` — a SHA-256 hash of the whole receipt (`executor/executor.py::_receipt_id`) | Computed inside EXECUTOR |

**Why case ≠ run matters here, concretely:** `case_context.case_id` is optional and, when present, is caller-supplied free text — nothing stops two different pipeline invocations from reusing the same `case_id` (a legitimate re-run: new evidence arrives, the case is re-adjudicated), and nothing stops a case from never repeating. If "case" and "run" were the same table, a re-run would either silently overwrite the first decision (destroying audit history — see §J) or force a synthetic uniqueness hack onto `case_id` that isn't part of the pipeline's contract.

**Both `decision_id` and `receipt_id` are content fingerprints, not event identifiers** — explicitly stated in both source design docs (`govern_layer_design.md` §P.2: *"a content fingerprint, not a unique event id"*). Two runs with byte-identical `case_context` + `weigh_output` produce the **same** `decision_id`. The data layer must not place a `UNIQUE` constraint on either hash (§K.3), or a legitimate replay will fail to insert.

---

## E. Entity model

Ten tables, matching the ten checkpoints in §5 of the brief, minus one merge and one split explained below:

| Brief's suggested entity | Decision |
|---|---|
| `cases` | **Kept.** Thin identity anchor only. |
| *(not in the brief, but required by §7)* | **Added: `case_runs`.** One row per pipeline execution. Everything else hangs off this. |
| `agent_outputs` | **Kept**, one row per contributing agent payload per run. |
| `conflicts` | **Kept**, 1:1 with `case_runs` today (documented, not hidden — see §G). |
| `resolve_results` / `candidates` | **Kept as `candidates` only.** A separate `resolve_results` table would carry no columns beyond `case_run_id` + `unresolved`, which already lives on `case_runs` (§F.2). Not created — see §Q. |
| `weigh_results` | **Kept**, 1:1 with `case_runs`. |
| — | **Added: `candidate_scores`.** Split out of `candidates` because WEIGH's own contract (`weigh_layer_design.md` §C.2 invariant 2) states WEIGH *only adds fields* to RESOLVE's candidates and never mutates the originals. Two tables make that append-only relationship structural rather than a convention someone can violate with an `UPDATE`. |
| `govern_results` | **Kept**, 1:1 with `case_runs`. |
| `execution_receipts` | **Kept**, 1:1 with `case_runs` (see §J for the edge case). |
| `audit_events` | **Kept** — justified in §I, not created reflexively. |

No `resolve_results` table, no per-objective columns, no per-constraint columns. Justification for each omission is inline in §F.

---

## F. Table-by-table schema

Conventions used throughout: `uuid` primary keys via `gen_random_uuid()` (the `pgcrypto` extension, standard in Supabase), `timestamptz` for all times, `numeric(p,s)` instead of `float`/`double precision` for anything that must reproduce the Python layer's rounding exactly (WEIGH rounds to 4dp everywhere — `weigh_layer_design.md` §F.1).

### F.1 `cases`

Identity only. No decision-bearing data.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | generated |
| `external_case_id` | `text` | nullable — from `case_context.case_id`; `NULL` when the caller never supplied one |
| `created_at` | `timestamptz` NOT NULL default `now()` | first time this case was seen |

Constraint: `UNIQUE (external_case_id)` where `external_case_id IS NOT NULL` (a Postgres partial unique index — `CREATE UNIQUE INDEX ON cases (external_case_id) WHERE external_case_id IS NOT NULL`). Multiple cases with no external id are allowed to coexist; nothing distinguishes them except their internal `id` and their runs.

### F.2 `case_runs`

The hub. One row per pipeline execution.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `case_id` | `uuid` NOT NULL FK → `cases(id)` | |
| `entity_type` | `text` NOT NULL | `"order_vendor"` \| `"customer"` today |
| `agent_a` | `text` NOT NULL | e.g. `"payouts"` |
| `agent_b` | `text` NOT NULL | e.g. `"dispute"` |
| `conflict` | `boolean` NOT NULL | echoed from `resolve_output.conflict` |
| `unresolved` | `boolean` NOT NULL | echoed from `resolve_output.unresolved` — replaces the never-built `resolve_results` table |
| `case_context` | `jsonb` NOT NULL | verbatim `case_context` dict passed into WEIGH/GOVERN — see §H.1 |
| `policy_id` | `text` NOT NULL | |
| `policy_version` | `text` NOT NULL | |
| `policy_hash` | `text` NOT NULL | canonical copy; WEIGH/GOVERN both echo it redundantly, this table is where it is stored once |
| `status` | `text` NOT NULL | denormalized read-model field — see §F.2.1 |
| `created_at` | `timestamptz` NOT NULL default `now()` | when this run started |

Index: `(case_id, created_at)` — every "show me this case's history" query.

#### F.2.1 `status` — the one deliberate denormalization

`status` mirrors `govern_results.outcome` once GOVERN has run, or one of two run-level states before/without a GOVERN row: `'IN_PROGRESS'` (agent outputs recorded, WEIGH/GOVERN not yet written) or `'FAILED'` (a layer raised — see §I). This exists purely so the case list page (§M) can filter and color-code without joining five tables per row. It is **written once, by the same process that writes `govern_results`**, and is never treated as authoritative — the authoritative outcome always lives in `govern_results.outcome`. A future consistency check can assert `case_runs.status = govern_results.outcome` for every completed run.

### F.3 `agent_outputs`

One row per agent payload the run consumed — the two conflict parties, plus any additional agents present in `agent_actions` purely as constraint evidence (`govern/conftest.py`'s `no_conflict_release_case(with_rto_verdict=True)` pattern).

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `case_run_id` | `uuid` NOT NULL FK → `case_runs(id)` | |
| `agent_name` | `text` NOT NULL | `"payouts"` \| `"dispute"` \| `"rto"` \| `"retention"` |
| `role` | `text` NOT NULL | `'agent_a'` \| `'agent_b'` \| `'extra'` — informative only, never decision-bearing (WEIGH deliberately made itself order-independent, `weigh_layer_design.md` §D.3) |
| `proposed_action` | `text` NOT NULL | |
| `confidence` | `numeric(4,3)` NOT NULL | 0.000–1.000 |
| `payload` | `jsonb` NOT NULL | full agent payload as produced by `mock_agents/*.py` — see §H.2 |
| `created_at` | `timestamptz` NOT NULL default `now()` | |

Index: `(case_run_id)`.

### F.4 `conflicts`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `case_run_id` | `uuid` NOT NULL UNIQUE FK → `case_runs(id)` | UNIQUE enforces today's 1:1 cardinality — see §G |
| `action_a` | `text` NOT NULL | |
| `action_b` | `text` NOT NULL | |
| `conflict` | `boolean` NOT NULL | |
| `reason` | `text` NOT NULL | conflict-matrix's human-readable reason string |
| `created_at` | `timestamptz` NOT NULL default `now()` | |

### F.5 `candidates`

RESOLVE's substance. Immutable once written — nothing downstream ever updates a row here.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | surrogate key — WEIGH's own docs warn `candidate_id` is unique only *within one output* (`weigh_layer_design.md` §D.6 note), never globally |
| `case_run_id` | `uuid` NOT NULL FK → `case_runs(id)` | |
| `candidate_id` | `text` NOT NULL | RESOLVE's local id, e.g. `"defer_to_agent-1"` |
| `strategy` | `text` NOT NULL | `DEFER_TO_AGENT` \| `HOLD_BOTH_PENDING_REVIEW` \| `NO_CONFLICT_PROCEED` \| `SUPPRESS_ACTION` |
| `preferred_agent` | `text` | nullable |
| `resulting_actions` | `text[]` NOT NULL | empty array for `HOLD_BOTH_PENDING_REVIEW` |
| `rationale` | `text` NOT NULL | |
| `source_rule` | `text` NOT NULL | |
| `created_at` | `timestamptz` NOT NULL default `now()` | |

Constraint: `UNIQUE (case_run_id, candidate_id)` — this is the exact composite key the WEIGH design doc tells its own audit-layer readers to use.

### F.6 `candidate_scores`

WEIGH's enrichment. One row per candidate, added after `candidates` and never edited afterward.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `candidate_row_id` | `uuid` NOT NULL UNIQUE FK → `candidates(id)` | 1:1 — the structural expression of "WEIGH only adds fields" |
| `total_score` | `numeric(6,4)` NOT NULL | ∈ [0,1] |
| `eligible` | `boolean` NOT NULL | |
| `eligibility_basis` | `text` NOT NULL | `"no_blocking_findings"` or `"blocked_by:HC_…"` |
| `rank` | `integer` NOT NULL | eligible-first ordering |
| `score_rank` | `integer` NOT NULL | pure-score ordering, ignores eligibility |
| `tie_group` | `integer` | nullable |
| `originating_agent` | `text` | nullable (`null` when `preferred_agent is None`) |
| `originating_confidence` | `numeric(4,3)` | nullable |
| `evidence_complete` | `boolean` NOT NULL | |
| `objective_impacts` | `jsonb` NOT NULL | the 5-objective breakdown — see §H.3 |
| `constraint_findings` | `jsonb` NOT NULL | array of advisory findings — see §H.3 |
| `created_at` | `timestamptz` NOT NULL default `now()` | |

### F.7 `weigh_results`

Run-level, 1:1 with `case_runs`.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `case_run_id` | `uuid` NOT NULL UNIQUE FK → `case_runs(id)` | |
| `weigh_version` | `text` NOT NULL | |
| `scoring_method` | `text` NOT NULL | `"weighted_linear_v1"` |
| `profile_name` | `text` NOT NULL | **not** `profile_selected` — see §B |
| `profile_reason` | `text` NOT NULL | `"matched_rule"` \| `"default"` |
| `matched_rule_index` | `integer` | nullable |
| `matched_rule` | `jsonb` | nullable |
| `weights_used` | `jsonb` NOT NULL | 5 floats keyed by objective — see §H.3 |
| `case_confidence` | `numeric(4,3)` NOT NULL | |
| `confidence_method` | `text` NOT NULL | `"min_blend_v1"` |
| `supporting_signals` | `integer` NOT NULL | |
| `evidence_complete` | `boolean` NOT NULL | |
| `ambiguity_detected` | `boolean` NOT NULL | |
| `ambiguity_signals` | `jsonb` NOT NULL | array, variable shape per signal code |
| `near_tie_group` | `text[]` | nullable |
| `top_gap` | `numeric(6,4)` | nullable |
| `constraint_evaluation` | `jsonb` NOT NULL | `constraints_checked`, `violated_candidate_ids`, `indeterminate_candidate_ids` |
| `notes` | `jsonb` NOT NULL default `'[]'` | |
| `raw_output` | `jsonb` NOT NULL | the complete, verbatim `weigh_output` document — see §H.4 |
| `created_at` | `timestamptz` NOT NULL default `now()` | |

### F.8 `govern_results`

Run-level, 1:1 with `case_runs`.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `case_run_id` | `uuid` NOT NULL UNIQUE FK → `case_runs(id)` | |
| `govern_version` | `text` NOT NULL | |
| `decision_method` | `text` NOT NULL | `"policy_gated_v1"` |
| `decision_id` | `text` NOT NULL | **indexed, not `UNIQUE`** — content fingerprint, see §D and §K.3 |
| `outcome` | `text` NOT NULL | ∈ `{PROCEED, HOLD, ESCALATE, AMBIGUOUS}` |
| `outcome_basis` | `text` NOT NULL | |
| `execution_authorized` | `boolean` NOT NULL | |
| `selected_candidate_row_id` | `uuid` FK → `candidates(id)` | nullable; non-null **only** when `outcome = 'PROCEED'` |
| `authorized_actions` | `text[]` NOT NULL default `'{}'` | |
| `candidate_under_review_row_id` | `uuid` FK → `candidates(id)` | nullable |
| `profile_selected` | `text` NOT NULL | GOVERN's own field name for this (echoes `weigh_output.profile.profile_name`) |
| `weights_used` | `jsonb` NOT NULL | |
| `objectives_considered` | `text[]` NOT NULL | |
| `score_band` | `jsonb` NOT NULL | |
| `permission_evaluation` | `jsonb` NOT NULL | per-candidate recheck/authority block — see §H.5 |
| `escalation` | `jsonb` NOT NULL | |
| `claude` | `jsonb` NOT NULL | gate/invoked/output_used/error/fallback_applied/advisory |
| `rationale` | `jsonb` NOT NULL | outcome_sentence/reasons/claude_narrative |
| `policy_hash` | `text` NOT NULL | re-echoed per `policy.audit.required_fields` |
| `raw_output` | `jsonb` NOT NULL | the complete, verbatim `govern_output` document |
| `created_at` | `timestamptz` NOT NULL default `now()` | |

Check constraint: `execution_authorized = (outcome = 'PROCEED')` — this is GOVERN's own single derivation rule (`govern_layer_design.md` §F.1), and encoding it as a DB check constraint catches a corrupted write without needing an app-level test to catch it first.

### F.9 `execution_receipts`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `case_run_id` | `uuid` NOT NULL UNIQUE FK → `case_runs(id)` | 1:1 for today's usage — see §J |
| `govern_result_id` | `uuid` NOT NULL FK → `govern_results(id)` | |
| `receipt_id` | `text` NOT NULL | **indexed, not `UNIQUE`** — same content-fingerprint reasoning as `decision_id` |
| `executor_version` | `text` NOT NULL | |
| `execution_method` | `text` NOT NULL | `"mock_execution_v1"` |
| `execution_mode` | `text` NOT NULL default `'mock'` | |
| `status` | `text` NOT NULL CHECK (`status IN ('EXECUTED','REJECTED')`) | |
| `authorization` | `jsonb` NOT NULL | the back-reference block (§H.6) |
| `authorization_checks` | `jsonb` NOT NULL | the ladder trail, in order |
| `executed_actions` | `jsonb` NOT NULL default `'[]'` | effect records |
| `rejection` | `jsonb` | nullable; non-null **only** when `status = 'REJECTED'` |
| `raw_output` | `jsonb` NOT NULL | the complete, verbatim receipt |
| `created_at` | `timestamptz` NOT NULL default `now()` | |

Check constraint: `(status = 'REJECTED') = (rejection IS NOT NULL)`.

### F.10 `audit_events`

Append-only. Justification is in §I — not created by default "audit logs are good" reasoning.

| Column | Type | Notes |
|---|---|---|
| `id` | `bigserial` PK | ordinary monotonic id is sufficient; this table is never joined for identity, only scanned in `occurred_at` order |
| `case_run_id` | `uuid` NOT NULL FK → `case_runs(id)` | |
| `stage` | `text` NOT NULL | `RUN_STARTED` \| `AGENTS_RECORDED` \| `CONFLICT_EVALUATED` \| `RESOLVE_COMPLETED` \| `WEIGH_COMPLETED` \| `GOVERN_DECIDED` \| `EXECUTOR_COMPLETED` \| `RUN_FAILED` |
| `outcome` | `text` NOT NULL | `'SUCCEEDED'` \| `'FAILED'` |
| `summary` | `text` NOT NULL | one human-readable line, e.g. `"GOVERN: PROCEED (SCORE_AT_OR_ABOVE_PROCEED_MIN)"` |
| `detail` | `jsonb` | nullable; small — an error message and type on failure, `null` on success (the full payload already lives in the stage's own table) |
| `occurred_at` | `timestamptz` NOT NULL default `now()` | |

Index: `(case_run_id, occurred_at)`.

---

## G. Relationships

```
cases (1) ────< (many) case_runs
case_runs (1) ────< (many) agent_outputs          [today: exactly 2, sometimes 3]
case_runs (1) ──── (0/1) conflicts                 [today: always exactly 1 once conflict-evaluated]
case_runs (1) ────< (many) candidates              [1, or 2 — RESOLVE emits 1 or 2 candidates today]
candidates (1) ──── (0/1) candidate_scores         [1:1 once WEIGH has run]
case_runs (1) ──── (0/1) weigh_results
case_runs (1) ──── (0/1) govern_results
govern_results (many) >──── (1) candidates          [selected_candidate_row_id, candidate_under_review_row_id]
case_runs (1) ──── (0/1) execution_receipts
execution_receipts (many) >──── (1) govern_results  [govern_result_id]
case_runs (1) ────< (many) audit_events
```

Primary/foreign keys as specified per table in §F. Every FK from a pipeline-stage table back to `case_runs` uses `ON DELETE CASCADE` **conceptually**, but see §L — rows are never deleted in normal operation, and if retention ever requires deletion it should be a deliberate, policy-driven job, not an implicit cascade a careless `DELETE FROM cases` triggers. Recommendation: `ON DELETE RESTRICT` everywhere, forcing any deletion to be explicit and ordered.

### ASCII ER diagram

```
                       ┌───────────┐
                       │   cases   │
                       │  id (PK)  │
                       │ external_ │
                       │  case_id  │
                       └─────┬─────┘
                             │ 1
                             │
                             │ *
                       ┌─────▼──────────────────────┐
                       │        case_runs            │
                       │  id (PK)                    │
                       │  case_id (FK)                │
                       │  entity_type, agent_a/b      │
                       │  conflict, unresolved         │
                       │  case_context (jsonb)          │
                       │  policy_id/version/hash          │
                       │  status                             │
                       └──┬──────┬────────┬────────┬────────┬─┘
              1:*          │      │1:0/1    │1:*      │0/1     │1:*
        ┌────────────┐     │  ┌───▼─────┐ ┌─▼──────┐ ┌▼───────┐ ┌▼───────────┐
        │agent_outputs│     │  │conflicts│ │candidates│ │weigh_  │ │audit_events│
        │case_run_id  │     │  │case_run_│ │case_run_│ │results │ │case_run_id │
        │agent_name   │     │  │id (UQ)  │ │id       │ │case_run│ │stage       │
        │role         │     │  └─────────┘ │candidate│ │_id(UQ) │ │occurred_at │
        │payload jsonb│     │              │_id      │ │raw_    │ └────────────┘
        └─────────────┘     │              └───┬─────┘ │output  │
                             │                  │1:0/1   └────────┘
                             │              ┌───▼──────────┐
                             │              │candidate_    │
                             │              │scores        │
                             │              │candidate_row_│
                             │              │id (UQ, FK)   │
                             │              │total_score   │
                             │              │objective_    │
                             │              │impacts jsonb │
                             │              └──────────────┘
                             │
                             │0/1                              0/1
                       ┌─────▼───────────┐                ┌────▼──────────────┐
                       │ govern_results   │───────────────>│ execution_receipts │
                       │ case_run_id(UQ)  │  govern_result_ │ case_run_id (UQ)   │
                       │ decision_id      │  id (FK)        │ receipt_id         │
                       │ outcome          │                 │ status             │
                       │ selected_        │                 │ authorization      │
                       │ candidate_row_id │─────┐           │  jsonb             │
                       │ (FK → candidates)│     │           └────────────────────┘
                       │ raw_output jsonb │     │
                       └──────────────────┘     │
                                                 └──> candidates.id
```

---

## H. JSONB decisions

The rule applied uniformly: **a field becomes a structured column when the UI or a query needs to filter/sort/join on it; it stays JSONB when its shape is inherited verbatim from a Python dict whose whole value is the auditable artifact.** Never both split *and* duplicated without a reason — every JSONB column below is justified individually.

### H.1 `case_runs.case_context` (jsonb)

`case_context` is caller-supplied, all-keys-optional, schema-light data (`weigh_layer_design.md` §D.4: `merchant_id`, `merchant_risk_tier`, `merchant_trust_tier`, `merchant_flags` — "all keys optional... unknown keys ignored"). Forcing it into fixed columns would silently drop any future key the Python layer starts reading, exactly the kind of drift the WEIGH design spent an entire section (§D.4) warning against. Stored whole; `case_runs.entity_type`/`agent_a`/`agent_b` are pulled out as columns only because every run has them and every UI list view needs them.

### H.2 `agent_outputs.payload` (jsonb)

Each mock agent (`mock_agents/*.py`) emits a different domain shape: `payouts` has `amount`/`invoice_id`/`days_overdue`; `dispute` has `dispute_status`/`disputed_amount`; `rto` has `rto_score`/`shipment_status`; `retention` has `churn_risk`/`customer_value_score`. A shared `agent_outputs` table with per-agent-type columns would need four sparsely-populated column families or four separate tables — over-normalization the brief explicitly warns against (§6: "avoid unnecessary normalization"). `agent_name`, `proposed_action`, and `confidence` are promoted to columns because they are the three fields every layer downstream actually reads by name; everything else stays in `payload`.

### H.3 `candidate_scores.objective_impacts` / `constraint_findings`, and `weigh_results.weights_used`

`objective_impacts` is a fixed 5-key object (`financial_exposure_prevention`, `fraud_risk_reduction`, `compliance_risk_reduction`, `merchant_trust`, `operational_cost`), each holding 4 sub-fields (`raw`, `normalized`, `weight`, `contribution`, `source`) — 25 scalar values per candidate. Flattening this into columns buys nothing: no UI or query in §M filters *by* an individual objective's contribution, and the entire point of storing it is §A's "check our arithmetic" auditability — a judge reading a receipt wants the whole breakdown at once, not a row reconstructed from 25 columns. `constraint_findings` is a variable-length array (0–5 findings depending on which constraints applied) with a different shape (`INDETERMINATE` findings carry different `observed` keys than `VIOLATED` ones) — a natural fit for JSONB, an awkward one for columns. `weights_used` is the same 5-key object at the profile level.

### H.4 `weigh_results.raw_output` / H.5 `govern_results.permission_evaluation`, `raw_output` / receipt `raw_output`

Every "results" table stores **both** structured columns for the fields the UI queries by, **and** a `raw_output` (or, for GOVERN's richest nested block, `permission_evaluation`) column holding the complete verbatim document. This is deliberate redundancy, not an oversight:

- **Structured columns exist for querying** — "list every `AMBIGUOUS` case this week," "average `case_confidence`" — without parsing JSON in the app layer.
- **`raw_output` exists as the tamper-evident, complete copy.** GOVERN's own contract invariant (`govern_layer_design.md` §C.4.3) requires `compute_policy_hash(policy) == weigh_output.policy_hash` to hold; the only way the data layer can *prove*, after the fact, that GOVERN saw the exact WEIGH document it claims to have seen is to have stored that document whole, not reconstructed from normalized fragments that a future schema migration could silently reinterpret.

`permission_evaluation` specifically is kept as one JSONB blob on `govern_results` rather than split into a `govern_candidate_evaluations` table. It is GOVERN's own re-check per candidate (constraint re-derivation, authority evaluation, governance gate) — rich, and not needed by any listed UI requirement in §M at the per-candidate level (the UI need is "why was this permitted/blocked," which the candidate-level `blocking_reasons` array inside the JSON already answers via simple client-side rendering). Normalizing it is flagged as a stretch option in §Q, not built now.

### H.6 `execution_receipts.authorization` / `authorization_checks`

`authorization` is EXECUTOR's own back-reference block (`_authorization_block` in `executor/executor.py`) — a flat object of ~12 fields, all already stored as columns elsewhere in `govern_results`. It is kept as JSONB on the receipt anyway because EXECUTOR's own design principle is that **the receipt is self-contained** ("every authorizing fact on the receipt is copied out of GOVERN's document" — `executor/executor.py` module docstring): an auditor should be able to read one receipt row without joining back to `govern_results` at all. `authorization_checks` is the ladder trail — an ordered list of `{check, result}` pairs, naturally an array, and its entire audit value (§I.2) is the *order and stopping point*, which a table would only re-derive with an extra `sequence` column for no benefit.

---

## I. Audit model

### I.1 Why `audit_events` earns its place

The eight preceding tables already carry `created_at` on every row, so "what happened, and when" is *mostly* reconstructable without a dedicated log. `audit_events` is still justified for one reason the result tables structurally cannot cover: **a stage that fails leaves no row in its own table.** If `weigh.evaluate_candidates` raises `WeighPolicyError` mid-run, there is no `weigh_results` row to query — and without a separate log, "did WEIGH run and fail, or did the orchestrator never reach it?" is unanswerable from the schema alone. `audit_events` exists specifically to hold that case (`stage = 'RUN_FAILED'`, `detail` carrying the error type/message), plus to give the case-detail page (§M) one `ORDER BY occurred_at` query for a human-readable timeline instead of a `UNION ALL` across eight differently-shaped tables.

It is explicitly **not** a duplicate of the result tables' content: `detail` is small (an error, or nothing) — never the full WEIGH/GOVERN/receipt document, which already lives in `raw_output`.

### I.2 The reconstruction query

*"Why did Sentinel execute this?"* — the judge's question from §8 of the brief — is answered by one join per case:

```
case_runs
  JOIN agent_outputs        ON agent_outputs.case_run_id = case_runs.id
  JOIN conflicts             ON conflicts.case_run_id = case_runs.id
  JOIN candidates            ON candidates.case_run_id = case_runs.id
  LEFT JOIN candidate_scores ON candidate_scores.candidate_row_id = candidates.id
  LEFT JOIN weigh_results    ON weigh_results.case_run_id = case_runs.id
  LEFT JOIN govern_results   ON govern_results.case_run_id = case_runs.id
  LEFT JOIN execution_receipts ON execution_receipts.case_run_id = case_runs.id
WHERE case_runs.id = :run_id
ORDER BY candidates.candidate_id
```

plus, separately, `audit_events WHERE case_run_id = :run_id ORDER BY occurred_at` for the timeline. Every fact needed for the chain in §8 (*agents → conflict → candidates → WEIGH → GOVERN → EXECUTOR*) is reachable in this one query, keyed throughout by `case_run_id` (or, for `candidate_scores`, transitively via `candidates.id`).

### I.3 Minimum fields for the chain (§8's actual ask)

| Link in the chain | Minimum fields |
|---|---|
| agents disagreed | `agent_outputs.proposed_action` (×2, same `case_run_id`, different `agent_name`) + `conflicts.conflict = true` |
| candidate options existed | `candidates.candidate_id`, `strategy`, `resulting_actions`, `rationale` |
| one scored highest | `candidate_scores.total_score`, `rank`, `eligible` |
| GOVERN allowed/blocked and why | `govern_results.outcome`, `outcome_basis`, `rationale` (jsonb), and — for a blocked candidate — `permission_evaluation` (jsonb, `blocking_reasons` per candidate) |
| EXECUTOR executed/rejected | `execution_receipts.status`, `executed_actions` or `rejection` |

---

## J. Idempotency / re-run strategy

**Every insert into `case_runs` is a new row.** Re-running the same case (same `external_case_id`, possibly different evidence) never updates a prior run — it creates a sibling `case_runs` row under the same `cases.id`. This is the direct consequence of §D: case identity and run identity are different things, and the entire "avoid confusing duplicate executions or losing historical decisions" requirement from §7 of the brief is satisfied by that separation alone, with no extra machinery:

- **Duplicate executions are not confusing** because each is its own `case_runs` row with its own `govern_results`/`execution_receipts` — nothing is overwritten, and the case-detail page (§M) can list every run for a case chronologically, most recent first, exactly like a version history.
- **No historical decision is lost** because nothing is ever `UPDATE`d after being written by the pipeline — every pipeline-stage table is insert-only in normal operation (the only mutation in the entire schema is the one denormalized `case_runs.status` write described in §F.2.1, and that happens exactly once per run, immediately after `govern_results` is inserted, never again).
- **`decision_id` and `receipt_id` are deliberately not unique constraints** (§D, §K.3): a genuine byte-identical replay (same `case_context`, same `weigh_output`) is expected to produce the same hash twice, in two different `case_runs` rows, and that must be allowed to insert cleanly rather than raise a constraint violation. Uniqueness of *storage* is provided by `case_runs.id`, not by the content hash.

**What "processing" identity buys beyond "case" identity, concretely:** the orchestrator can safely call the pipeline twice for the same case_id — once during a demo dry run, once for the real judged run — and both are preserved, distinguishable, and independently auditable, without the caller needing to invent its own run-numbering scheme.

No idempotency key, no deduplication trigger, and no "latest run wins" logic is built into the schema. If the product later needs "show me only the authoritative run for this case," that is a read-model decision (`ORDER BY case_runs.created_at DESC LIMIT 1`), not a write-time constraint — building the constraint now would be inventing complexity the current architecture does not ask for (§7: "do not invent complexity unless the actual architecture requires it").

---

## K. Indexes and constraints

### K.1 Primary/foreign keys

Specified per table in §F. All FKs `NOT NULL` except the two GOVERN candidate references (`selected_candidate_row_id`, `candidate_under_review_row_id`, both nullable per outcome) and `execution_receipts.rejection`/`govern_results.selected_candidate_row_id`.

### K.2 Indexes

| Table | Index | Purpose |
|---|---|---|
| `cases` | partial unique on `external_case_id` (not null) | case lookup by business id |
| `case_runs` | `(case_id, created_at)` | case history, chronological |
| `case_runs` | `(status)` | case-list filtering |
| `agent_outputs` | `(case_run_id)` | join fan-out |
| `candidates` | unique `(case_run_id, candidate_id)` | the WEIGH-mandated composite key |
| `candidate_scores` | unique `(candidate_row_id)` | 1:1 enforcement |
| `weigh_results`, `govern_results`, `execution_receipts` | unique `(case_run_id)` | 1:1 enforcement |
| `govern_results` | `(decision_id)` — non-unique btree | audit lookup by decision id |
| `execution_receipts` | `(receipt_id)` — non-unique btree | audit lookup by receipt id |
| `audit_events` | `(case_run_id, occurred_at)` | timeline query |

### K.3 Constraints worth stating explicitly (recap)

- `govern_results`: `CHECK (execution_authorized = (outcome = 'PROCEED'))`.
- `govern_results`: `selected_candidate_row_id IS NOT NULL` only enforceable at the app layer (a `CHECK` referencing `outcome` and nullability together is expressible in Postgres via a `CHECK` constraint, e.g. `CHECK ((outcome = 'PROCEED') = (selected_candidate_row_id IS NOT NULL))` — include it).
- `execution_receipts`: `CHECK ((status = 'REJECTED') = (rejection IS NOT NULL))`.
- No `UNIQUE` on `decision_id` or `receipt_id` (§D, §J) — the one constraint decision in this document that inverts the usual instinct, stated twice on purpose because it is easy to "fix" by mistake later.

---

## L. RLS direction

Buildathon-appropriate, not enterprise multi-tenant. Two facts ground this:

1. There is no auth/user/tenant concept anywhere in the current backend — no `User` model, no session, no org boundary. Inventing a multi-tenant RLS design now would be designing against a requirement that does not exist (§10 of the brief: "do not design a complex multi-tenant enterprise authorization system").
2. The Python backend, not Supabase, is the only writer with any business logic. Nothing about who is allowed to *write* a case run is a governance decision — it is purely "is this the trusted backend service."

**Recommendation:**

- All ten tables: RLS **enabled** (Supabase default best practice), with two policies each:
  - **Service-role write policy**: only the backend's service-role key (bypasses RLS by default in Supabase, or an explicit `service_role` policy) may `INSERT`. No `UPDATE`/`DELETE` policy is granted to any role in normal operation — enforcing the insert-only model from §J at the database level, not just by convention.
  - **Authenticated read policy**: any authenticated user may `SELECT` all rows. There is exactly one class of user in this project (the demo/judge-facing UI's users), so a single permissive read policy is correct; do not build per-case row ownership.
- The anonymous (`anon`) role gets no policy at all — the UI must authenticate, even if authentication is a single shared demo credential.

This is intentionally the simplest RLS shape that still uses RLS correctly (deny-by-default, explicit grants) rather than disabling it. If a future phase introduces real user accounts or merchant-scoped access, the read policy is the only thing that changes — add a `WHERE` clause keyed on a merchant/user column that does not exist today. Do not build that column now.

---

## M. UI read requirements

The case-detail page needs, in order:

| UI element | Source |
|---|---|
| Case header (id, entity type, created, status) | `case_runs` (+`cases.external_case_id`) |
| "These agents disagreed" | `agent_outputs` (2+ rows) + `conflicts.conflict/reason` |
| "These were the candidate options" | `candidates` (`strategy`, `resulting_actions`, `rationale`) |
| "This option scored highest" | `candidate_scores` (`total_score`, `rank`) joined to `candidates` |
| Full arithmetic breakdown (expandable) | `candidate_scores.objective_impacts` |
| "GOVERN allowed/blocked it because…" | `govern_results.outcome`, `outcome_basis`, `rationale.outcome_sentence`, `permission_evaluation` for per-candidate blocking reasons |
| "Executor executed/rejected it" | `execution_receipts.status`, `executed_actions`, `rejection` |
| Case timeline | `audit_events` ordered by `occurred_at` |
| Case list / search | `case_runs.status`, `case_runs.created_at`, `cases.external_case_id` |

Every one of these is a direct column or a one-level JSONB field read — no aggregation, no computed column, no view logic that re-derives anything. If a future page needs a cross-case aggregate (e.g., "% of cases escalated this week"), that is a `SELECT ... GROUP BY status` over `case_runs` — no schema change required.

---

## N. Example case lifecycle

Using the real fixture from `govern/conftest.py::payout_vs_dispute_case` (also the worked example in `govern_layer_design.md` §S.1 — `defer_to_agent-1` scores exactly `0.7500`, the PROCEED boundary):

1. **`cases`**: one row inserted (or found) for `external_case_id = 'case-Q'`.
2. **`case_runs`**: one row — `entity_type='order_vendor'`, `agent_a='payouts'`, `agent_b='dispute'`, `case_context={"case_id": "case-Q", "merchant_id": "mrch_001"}`, `status='IN_PROGRESS'`.
3. **`agent_outputs`**: two rows — `payouts` (`RELEASE_PAYMENT`, confidence `0.95`, payload `{amount: 42000, days_overdue: 9, ...}`), `dispute` (`HOLD_RELATED_ACTIONS`, confidence `0.95`, payload `{dispute_status: "OPEN", disputed_amount: 42000, ...}`).
4. **`conflicts`**: one row — `action_a='RELEASE_PAYMENT'`, `action_b='HOLD_RELATED_ACTIONS'`, `conflict=true`, `reason='Payment release overlaps with a dispute-related hold.'`.
5. **`candidates`**: two rows — `defer_to_agent-1` (`DEFER_TO_AGENT`, preferred `dispute`, resulting `['HOLD_RELATED_ACTIONS']`) and `hold_both_pending_review-2` (`HOLD_BOTH_PENDING_REVIEW`, resulting `[]`).
6. **`candidate_scores`**: two rows — `defer_to_agent-1` at `total_score=0.7500`, `eligible=true`, `rank=1`; `hold_both_pending_review-2` at its own score, `rank=2`.
7. **`weigh_results`**: one row — `profile_name='standard'`, `case_confidence=0.95`, `ambiguity_detected=false`, `raw_output=<full weigh_output>`.
8. **`govern_results`**: one row — `outcome='PROCEED'`, `outcome_basis='SCORE_AT_OR_ABOVE_PROCEED_MIN'`, `execution_authorized=true`, `selected_candidate_row_id` → the `defer_to_agent-1` row, `authorized_actions=['HOLD_RELATED_ACTIONS']`.
9. **`case_runs.status`** updated to `'PROCEED'`.
10. **`execution_receipts`**: one row — `status='EXECUTED'`, `executed_actions=[{action: 'HOLD_RELATED_ACTIONS', effect: 'RELATED_ACTIONS_HELD', ...}]`.
11. **`audit_events`**: seven rows, one per stage (`RUN_STARTED` → `AGENTS_RECORDED` → `CONFLICT_EVALUATED` → `RESOLVE_COMPLETED` → `WEIGH_COMPLETED` → `GOVERN_DECIDED` → `EXECUTOR_COMPLETED`), each `outcome='SUCCEEDED'`.

A re-run of the same case with a corrected `days_overdue` value produces a **second** `case_runs` row under the same `cases.id`, with its own complete set of rows 3–11. The first run's rows are untouched.

---

## O. Example reconstructed audit trail

For the case above, a judge asking *"why did Sentinel release this payment?"* gets, from the §I.2 query:

> Case `case-Q`: agents `payouts` and `dispute` disagreed — `payouts` proposed `RELEASE_PAYMENT` (confidence 0.95), `dispute` proposed `HOLD_RELATED_ACTIONS` (confidence 0.95) — flagged as a conflict ("Payment release overlaps with a dispute-related hold."). RESOLVE generated two options: defer to `dispute` (hold), or hold both pending review. WEIGH scored `defer_to_agent-1` at **0.7500** under the `standard` policy profile — the highest of the two, and eligible (no hard constraint blocked it). GOVERN independently re-checked the same constraints from raw evidence, confirmed the score met `proceed_min_score` (0.75), and authorized `HOLD_RELATED_ACTIONS` under decision `dec_…`. EXECUTOR verified that authorization against GOVERN's own permission record and executed it: the dispute case's related actions were placed on hold (`RELATED_ACTIONS_HELD`), receipt `exe_…`.

Every clause in that paragraph traces to a named column or JSONB field in §I.3 — nothing in the reconstruction is inferred or re-computed by the database.

---

## P. Supabase implementation plan (not built in this phase)

1. Create the Supabase project; enable the `pgcrypto` extension for `gen_random_uuid()`.
2. Write the ten `CREATE TABLE` statements per §F, in dependency order (`cases` → `case_runs` → the rest).
3. Add the indexes and check constraints from §K.
4. Enable RLS on all ten tables per §L; write the service-role insert policy and the authenticated select policy.
5. Write a thin Python adapter (`backend/persistence/` or similar — **not built in this task**) with one function per pipeline stage (`record_case_run`, `record_agent_outputs`, `record_conflict`, `record_candidates`, `record_weigh_result`, `record_govern_result`, `record_execution_receipt`, `record_audit_event`), each taking the exact dict the corresponding layer already returns and mapping it onto the columns in §F. No transformation logic beyond field selection — if a function needs to compute something the pipeline didn't already hand it, that is a sign the schema is wrong, not that the adapter needs to get smarter.
6. Wrap the whole per-run sequence in one Postgres transaction so a failure partway through (e.g., GOVERN raises) leaves the `RUN_FAILED` audit event as the only new fact, never a half-written `govern_results` row.
7. Wire the FastAPI layer (`backend/main.py`) to call the adapter after each stage, and add read endpoints backed by the queries in §I.2 and §M.

None of this is implemented as part of this document.

---

## Q. Open questions / decisions requiring approval

1. **The existing `backend/database/models.py` is superseded scaffolding, not a base to build on.** It defines `AgentAction`, `GovernanceDecision`, and `EvalCase` tables — but grepping the codebase shows **none of them is ever written to or read from anywhere outside `models.py` itself**. Their shapes predate WEIGH/GOVERN/EXECUTOR entirely: `GovernanceDecision` has `scenario`, `action`, `confidence`, `reasoning_text`, `evidence_ids`, `human_approval_required`, `safety_override_applied`, `final_outcome` — none of which map onto the real `govern_output` schema (no `policy_hash`, no `decision_id`, no `candidates`, no `outcome ∈ {PROCEED, HOLD, ESCALATE, AMBIGUOUS}`). **Recommendation (needs your approval): treat these three tables as dead scaffolding to be removed when the real persistence layer is implemented, not migrated.** The other eight models in that file (`Vendor`, `Payment`, `Dispute`, `Order`, `Customer`, `Subscription`, `RTOFlag`, `SupportNote`) are a *different* concern — mock world-state/reference data that a real (non-mock) agent implementation might eventually read from — and are out of scope for this design either way. Not touched; flagged only.
2. **The project's only persistence today is SQLite via SQLAlchemy** (`backend/database/connection.py`, `DATABASE_URL = "sqlite:///./sentinel.db"`), not Postgres. Moving to Supabase is a new dependency and connection string, not a migration of existing data — there is no data in the SQLite file worth migrating (confirmed: nothing writes to it). Needs approval before any implementation phase touches `requirements.txt` or adds a Supabase client.
3. **`case_runs.status` denormalization (§F.2.1) is a judgment call**, not something the brief mandates. The alternative is a view (`CREATE VIEW case_summary AS SELECT case_runs.*, govern_results.outcome AS status FROM case_runs LEFT JOIN govern_results ...`) instead of a stored column, trading one denormalized write for a join on every case-list read. Given a buildathon's low write volume and the judge-facing UI's read-heavy pattern, the stored column is recommended, but this is worth confirming rather than assuming.
4. **`permission_evaluation` and `authorization`/`authorization_checks` are left as JSONB rather than normalized further** (§H.5, §H.6). If the UI later needs to render a *per-candidate* permission table (not just the winning candidate's), a `govern_permission_evaluations` table keyed by `(govern_result_id, candidate_id)` would be a clean additive change — flagged as a stretch option, not built now, because no UI requirement in §M currently asks for it.
5. **No `entity_type`-specific tables were created** (e.g., a `order_vendor_cases` vs `customer_cases` split) even though `entity_type` currently takes exactly two values. The single `case_runs.entity_type text` column is deliberately generic — RESOLVE's rule table (`resolve/rules.py`) is the only place that would need to grow if a third entity type appeared, and the schema should not need to change in step with it.

---

## Final verification

`git status` after writing this document shows exactly one new file: `docs/data_layer_design.md`. No other file in the repository was created, modified, or deleted. Nothing was committed.
