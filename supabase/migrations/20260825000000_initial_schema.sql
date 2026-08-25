-- Sentinel data layer — initial schema
--
-- Authoritative design: docs/data_layer_design.md
-- This migration implements exactly the ten tables specified in that document
-- (§F), the relationships in §G, the JSONB decisions in §H, the indexes and
-- constraints in §K, and the RLS direction in §L. It creates no logic beyond
-- persistence: no triggers that decide anything, no re-derivation of scores
-- or authorization. GOVERN remains the sole authorization boundary; this
-- schema and its RLS policies only control database access.
--
-- Tables are created in dependency order: cases -> case_runs -> the rest.

create extension if not exists pgcrypto;

-- ============================================================================
-- cases — thin identity anchor only (design §F.1)
-- ============================================================================

create table cases (
    id uuid primary key default gen_random_uuid(),
    external_case_id text,
    created_at timestamptz not null default now()
);

-- Partial unique index: multiple cases with no external id may coexist;
-- only non-null external ids must be unique (design §F.1).
create unique index cases_external_case_id_key
    on cases (external_case_id)
    where external_case_id is not null;

-- ============================================================================
-- case_runs — the hub; one row per pipeline execution (design §F.2)
-- ============================================================================

create table case_runs (
    id uuid primary key default gen_random_uuid(),
    case_id uuid not null references cases (id) on delete restrict,
    entity_type text not null,
    agent_a text not null,
    agent_b text not null,
    conflict boolean not null,
    unresolved boolean not null,
    case_context jsonb not null,
    policy_id text not null,
    policy_version text not null,
    policy_hash text not null,
    -- Denormalized read-model field (design §F.2.1): mirrors
    -- govern_results.outcome once GOVERN has run, or 'IN_PROGRESS' /
    -- 'FAILED' before/without one. Written once by the same process that
    -- writes govern_results; govern_results.outcome remains authoritative.
    status text not null,
    created_at timestamptz not null default now()
);

create index case_runs_case_id_created_at_idx on case_runs (case_id, created_at);
create index case_runs_status_idx on case_runs (status);

-- ============================================================================
-- agent_outputs — one row per agent payload consumed by the run (design §F.3)
-- ============================================================================

create table agent_outputs (
    id uuid primary key default gen_random_uuid(),
    case_run_id uuid not null references case_runs (id) on delete restrict,
    agent_name text not null,
    role text not null check (role in ('agent_a', 'agent_b', 'extra')),
    proposed_action text not null,
    confidence numeric(4, 3) not null check (confidence >= 0 and confidence <= 1),
    -- Full agent payload as produced by mock_agents/*.py. Each agent emits a
    -- different domain shape; kept whole rather than split into sparse
    -- per-agent-type columns (design §H.2).
    payload jsonb not null,
    created_at timestamptz not null default now()
);

create index agent_outputs_case_run_id_idx on agent_outputs (case_run_id);

-- ============================================================================
-- conflicts — 1:1 with case_runs today (design §F.4, §G)
-- ============================================================================

create table conflicts (
    id uuid primary key default gen_random_uuid(),
    case_run_id uuid not null unique references case_runs (id) on delete restrict,
    action_a text not null,
    action_b text not null,
    conflict boolean not null,
    reason text not null,
    created_at timestamptz not null default now()
);

-- ============================================================================
-- candidates — RESOLVE's substance; immutable once written (design §F.5)
-- ============================================================================

create table candidates (
    id uuid primary key default gen_random_uuid(),
    case_run_id uuid not null references case_runs (id) on delete restrict,
    -- RESOLVE's local id, unique only within one output, never globally
    -- (weigh_layer_design.md §D.6) — hence the composite unique constraint
    -- below rather than a unique constraint on candidate_id alone.
    candidate_id text not null,
    strategy text not null check (
        strategy in (
            'DEFER_TO_AGENT',
            'HOLD_BOTH_PENDING_REVIEW',
            'NO_CONFLICT_PROCEED',
            'SUPPRESS_ACTION'
        )
    ),
    preferred_agent text,
    -- Empty array for HOLD_BOTH_PENDING_REVIEW.
    resulting_actions text[] not null,
    rationale text not null,
    source_rule text not null,
    created_at timestamptz not null default now(),
    constraint candidates_case_run_id_candidate_id_key unique (case_run_id, candidate_id)
);

-- ============================================================================
-- candidate_scores — WEIGH's enrichment; 1:1 with candidates (design §F.6)
-- ============================================================================

create table candidate_scores (
    id uuid primary key default gen_random_uuid(),
    -- 1:1 — the structural expression of "WEIGH only adds fields, never
    -- mutates the originals" (weigh_layer_design.md §C.2 invariant 2).
    candidate_row_id uuid not null unique references candidates (id) on delete restrict,
    total_score numeric(6, 4) not null check (total_score >= 0 and total_score <= 1),
    eligible boolean not null,
    eligibility_basis text not null,
    rank integer not null,
    score_rank integer not null,
    tie_group integer,
    originating_agent text,
    originating_confidence numeric(4, 3),
    evidence_complete boolean not null,
    -- 5-objective breakdown; no UI/query filters by an individual
    -- objective's contribution, so the full structure stays whole
    -- (design §H.3).
    objective_impacts jsonb not null,
    -- Variable-length array, shape depends on which constraints applied
    -- (design §H.3).
    constraint_findings jsonb not null,
    created_at timestamptz not null default now()
);

-- ============================================================================
-- weigh_results — run-level, 1:1 with case_runs (design §F.7)
-- ============================================================================

create table weigh_results (
    id uuid primary key default gen_random_uuid(),
    case_run_id uuid not null unique references case_runs (id) on delete restrict,
    weigh_version text not null,
    scoring_method text not null,
    -- Not profile_selected — weigh/profile.py emits profile_name; see
    -- design §B.
    profile_name text not null,
    profile_reason text not null check (profile_reason in ('matched_rule', 'default')),
    matched_rule_index integer,
    matched_rule jsonb,
    -- 5 floats keyed by objective (design §H.3).
    weights_used jsonb not null,
    case_confidence numeric(4, 3) not null check (case_confidence >= 0 and case_confidence <= 1),
    confidence_method text not null,
    supporting_signals integer not null,
    evidence_complete boolean not null,
    ambiguity_detected boolean not null,
    ambiguity_signals jsonb not null,
    near_tie_group text[],
    top_gap numeric(6, 4),
    constraint_evaluation jsonb not null,
    notes jsonb not null default '[]',
    -- Complete, verbatim weigh_output document — the tamper-evident copy
    -- (design §H.4).
    raw_output jsonb not null,
    created_at timestamptz not null default now()
);

-- ============================================================================
-- govern_results — run-level, 1:1 with case_runs (design §F.8)
-- ============================================================================

create table govern_results (
    id uuid primary key default gen_random_uuid(),
    case_run_id uuid not null unique references case_runs (id) on delete restrict,
    govern_version text not null,
    decision_method text not null,
    -- Content fingerprint (SHA-256 of {govern_version, policy_hash,
    -- case_context, weigh_output}), not an event id. Deliberately NOT
    -- UNIQUE — a byte-identical replay is expected to produce the same
    -- hash across two different case_runs rows (design §D, §J, §K.3).
    decision_id text not null,
    outcome text not null check (outcome in ('PROCEED', 'HOLD', 'ESCALATE', 'AMBIGUOUS')),
    outcome_basis text not null,
    execution_authorized boolean not null,
    selected_candidate_row_id uuid references candidates (id) on delete restrict,
    authorized_actions text[] not null default '{}',
    candidate_under_review_row_id uuid references candidates (id) on delete restrict,
    -- GOVERN's own field name for this (echoes weigh_output.profile.profile_name).
    profile_selected text not null,
    weights_used jsonb not null,
    objectives_considered text[] not null,
    score_band jsonb not null,
    -- GOVERN's own re-check per candidate; not split into a per-candidate
    -- table because no listed UI requirement needs that granularity today
    -- (design §H.5, §Q.4).
    permission_evaluation jsonb not null,
    escalation jsonb not null,
    claude jsonb not null,
    rationale jsonb not null,
    policy_hash text not null,
    -- Complete, verbatim govern_output document (design §H.4).
    raw_output jsonb not null,
    created_at timestamptz not null default now(),
    -- GOVERN's own single derivation rule (govern_layer_design.md §F.1),
    -- encoded so a corrupted write is caught at the database level.
    constraint govern_results_execution_authorized_matches_outcome
        check (execution_authorized = (outcome = 'PROCEED')),
    -- selected_candidate_row_id is populated if and only if outcome is
    -- PROCEED (design §F.8, §K.3).
    constraint govern_results_selected_candidate_matches_outcome
        check ((outcome = 'PROCEED') = (selected_candidate_row_id is not null))
);

create index govern_results_decision_id_idx on govern_results (decision_id);

-- ============================================================================
-- execution_receipts — 1:1 with case_runs for today's usage (design §F.9)
-- ============================================================================

create table execution_receipts (
    id uuid primary key default gen_random_uuid(),
    case_run_id uuid not null unique references case_runs (id) on delete restrict,
    govern_result_id uuid not null references govern_results (id) on delete restrict,
    -- Content fingerprint (SHA-256 of the whole receipt), same
    -- non-unique reasoning as govern_results.decision_id (design §D, §K.3).
    receipt_id text not null,
    executor_version text not null,
    execution_method text not null,
    execution_mode text not null default 'mock',
    status text not null check (status in ('EXECUTED', 'REJECTED')),
    -- EXECUTOR's own back-reference block, kept whole so an auditor can
    -- read one receipt row without joining back to govern_results
    -- (design §H.6).
    authorization jsonb not null,
    -- Ordered ladder trail; audit value is the order and stopping point
    -- (design §H.6).
    authorization_checks jsonb not null,
    executed_actions jsonb not null default '[]',
    rejection jsonb,
    -- Complete, verbatim receipt (design §H.4).
    raw_output jsonb not null,
    created_at timestamptz not null default now(),
    constraint execution_receipts_rejection_matches_status
        check ((status = 'REJECTED') = (rejection is not null))
);

create index execution_receipts_receipt_id_idx on execution_receipts (receipt_id);

-- ============================================================================
-- audit_events — append-only timeline (design §F.10, §I)
-- ============================================================================

create table audit_events (
    id bigserial primary key,
    case_run_id uuid not null references case_runs (id) on delete restrict,
    stage text not null check (
        stage in (
            'RUN_STARTED',
            'AGENTS_RECORDED',
            'CONFLICT_EVALUATED',
            'RESOLVE_COMPLETED',
            'WEIGH_COMPLETED',
            'GOVERN_DECIDED',
            'EXECUTOR_COMPLETED',
            'RUN_FAILED'
        )
    ),
    outcome text not null check (outcome in ('SUCCEEDED', 'FAILED')),
    summary text not null,
    -- Small: an error message and type on failure, null on success. The
    -- full payload already lives in the stage's own raw_output column
    -- (design §F.10, §I.1).
    detail jsonb,
    occurred_at timestamptz not null default now()
);

create index audit_events_case_run_id_occurred_at_idx on audit_events (case_run_id, occurred_at);

-- ============================================================================
-- Row Level Security (design §L)
--
-- No auth/user/tenant concept exists anywhere in the current backend, and
-- Supabase RLS is never the business authorization boundary — GOVERN is.
-- This is the simplest RLS shape that still uses RLS correctly
-- (deny-by-default, explicit grants): the trusted backend writes via the
-- service role (which bypasses RLS in Supabase by default), any
-- authenticated caller may read everything, and the anonymous role gets no
-- policy at all. No UPDATE/DELETE policy is granted to any role, enforcing
-- the insert-only model from design §J at the database level.
-- ============================================================================

alter table cases enable row level security;
alter table case_runs enable row level security;
alter table agent_outputs enable row level security;
alter table conflicts enable row level security;
alter table candidates enable row level security;
alter table candidate_scores enable row level security;
alter table weigh_results enable row level security;
alter table govern_results enable row level security;
alter table execution_receipts enable row level security;
alter table audit_events enable row level security;

create policy service_role_insert_cases on cases for insert to service_role with check (true);
create policy authenticated_select_cases on cases for select to authenticated using (true);

create policy service_role_insert_case_runs on case_runs for insert to service_role with check (true);
create policy authenticated_select_case_runs on case_runs for select to authenticated using (true);

create policy service_role_insert_agent_outputs on agent_outputs for insert to service_role with check (true);
create policy authenticated_select_agent_outputs on agent_outputs for select to authenticated using (true);

create policy service_role_insert_conflicts on conflicts for insert to service_role with check (true);
create policy authenticated_select_conflicts on conflicts for select to authenticated using (true);

create policy service_role_insert_candidates on candidates for insert to service_role with check (true);
create policy authenticated_select_candidates on candidates for select to authenticated using (true);

create policy service_role_insert_candidate_scores on candidate_scores for insert to service_role with check (true);
create policy authenticated_select_candidate_scores on candidate_scores for select to authenticated using (true);

create policy service_role_insert_weigh_results on weigh_results for insert to service_role with check (true);
create policy authenticated_select_weigh_results on weigh_results for select to authenticated using (true);

create policy service_role_insert_govern_results on govern_results for insert to service_role with check (true);
create policy authenticated_select_govern_results on govern_results for select to authenticated using (true);

create policy service_role_insert_execution_receipts on execution_receipts for insert to service_role with check (true);
create policy authenticated_select_execution_receipts on execution_receipts for select to authenticated using (true);

create policy service_role_insert_audit_events on audit_events for insert to service_role with check (true);
create policy authenticated_select_audit_events on audit_events for select to authenticated using (true);
