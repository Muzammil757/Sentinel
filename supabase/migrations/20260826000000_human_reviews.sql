-- Sentinel data layer — human review audit trail
--
-- Additive migration only: no existing table is altered. Adds one new table
-- for POST /api/cases/{case_id}/review (docs/data_layer_design.md has no
-- table for human review actions -- this fills that gap with the smallest
-- safe model).
--
-- A human review action here is PURE ANNOTATION. It never mutates
-- case_runs, govern_results, or execution_receipts, and it never triggers
-- EXECUTOR. GOVERN's original decision (outcome, execution_authorized) is
-- immutable and remains the sole authorization record. This table exists
-- only so a reviewer's approve/reject/request_more_evidence action -- and
-- the case/run state at the moment they took it -- is durably auditable.
--
-- "override" is deliberately not a legal action here: the current
-- architecture has no policy or authorization model for a human overriding
-- GOVERN, so the API layer refuses override requests before they ever reach
-- persistence rather than inventing one casually.

create table human_reviews (
    id uuid primary key default gen_random_uuid(),
    case_run_id uuid not null references case_runs (id) on delete restrict,
    action text not null check (action in ('approve', 'reject', 'request_more_evidence')),
    reviewer text,
    reason text,
    -- Snapshot of govern_results.outcome / case_runs.status at the moment of
    -- review, for audit context only -- never read back to decide anything.
    case_run_status_at_review text not null,
    created_at timestamptz not null default now()
);

create index human_reviews_case_run_id_created_at_idx on human_reviews (case_run_id, created_at);

alter table human_reviews enable row level security;

create policy service_role_insert_human_reviews
    on human_reviews for insert
    to service_role
    with check (true);

create policy authenticated_select_human_reviews
    on human_reviews for select
    to authenticated
    using (true);
