# Sentinel

Sentinel is a governance/decision pipeline for resolving conflicting recommendations from multiple autonomous agents. When two (or more) agents propose actions that disagree — e.g. a Payouts agent wants to release a payment while a Dispute agent wants to hold related actions — Sentinel deterministically detects the conflict, generates candidate resolutions, scores them against policy, authorizes (or blocks/escalates) a decision, and executes it under a fail-closed authorization boundary. Every stage of that process is persisted for full auditability.

Built for the Razorpay Buildathon as a demonstration of policy-driven, auditable multi-agent governance — not a live payments integration. All agent inputs in this repository come from deterministic mock agents (`backend/mock_agents/`), and execution is a recorded mock effect, never a real payment or account action.

## Architecture

```
Agents
  -> Conflict Matrix
  -> RESOLVE
  -> WEIGH
  -> GOVERN
  -> EXECUTOR
  -> Persistence (Supabase)
  -> API (FastAPI)
  -> Web UI
```

All decision-making happens in the Python backend (`backend/conflict_matrix/`, `backend/resolve/`, `backend/weigh/`, `backend/govern/`, `backend/executor/`). **Supabase is persistence, audit-trail, and read-model infrastructure only** — it stores what the pipeline decided and lets the API read it back; it never makes, re-derives, or influences a decision. No decision logic exists in the API layer, the frontend, or in Supabase (no scoring/authorization triggers or functions).

## How a decision works

1. **Agents** each propose an action from their own narrow view of a case (e.g. Payouts proposes `RELEASE_PAYMENT`, Dispute proposes `HOLD_RELATED_ACTIONS`).
2. **Conflict Matrix** deterministically checks whether the two proposed actions conflict for the given entity type.
3. **RESOLVE** generates candidate resolutions (e.g. defer to one agent, or hold both pending review) for the pipeline to evaluate.
4. **WEIGH** scores every candidate against the active policy — objective weights, hard-constraint checks, confidence, and ambiguity detection — producing a ranked, eligibility-annotated result.
5. **GOVERN** is the sole authorization boundary: it re-checks constraints, applies authority limits, and decides the case outcome (`PROCEED`, `HOLD`, `ESCALATE`, or `AMBIGUOUS`), setting `execution_authorized` accordingly.
6. **EXECUTOR** obeys GOVERN and nothing else. It is fail-closed: a receipt is `EXECUTED` only if every check in its authorization ladder passes; anything else — including any internal error — produces a `REJECTED` receipt, never a silent success and never a raised exception that skips a record.
7. **Persistence** writes every stage's output (agents, conflict, candidates, scores, WEIGH result, GOVERN result, execution receipt, audit events) to Supabase, verbatim, as it happens — nothing here re-scores or re-decides anything.

## Demo scenarios (Scenario Lab)

`backend/api/scenarios.py` defines a fixed, deterministic set of demo cases (normal payout, agent disagreement held for review, authority-cap escalation, an ambiguous near-tie, an executor rejection, and a deliberate pipeline failure). Each one runs through the exact same real pipeline a live case would (`POST /api/cases/{case_id}/run` under the hood) — nothing about a scenario's outcome is hard-coded; the pipeline decides it fresh every run from the fixed input evidence.

**The Scenario Lab does not call any external LLM or third-party API and does not consume external API credits.** GOVERN's optional advisor port (`backend/govern/advisor.py`) defaults to `None`, which is documented in that module as "the demo-safe path: with no advisor, GOVERN is pure deterministic arithmetic over policy data and no model is involved" — and nothing in this repository wires a real advisor into it. The only network call the Scenario Lab (or any case run) makes is to your own configured Supabase project. This is the current, safe way to demonstrate Sentinel end-to-end; there is no separate external-API-quota fallback mechanism, because none is needed for this pipeline to run.

## Real Supabase

Sentinel persists every pipeline run to a Supabase/PostgreSQL project (`supabase/migrations/`). The backend needs exactly two environment variables:

```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

Only the **names** are documented here — never their values (see `.env.example`). The service-role key is read only by `backend/persistence/connection.py`, server-side, and must never be exposed to the frontend. The frontend (`frontend/`) never contains a Supabase URL, key, or any other credential — it talks only to this backend's own `/api/*` endpoints, served same-origin.

## Setup

1. Clone the repository.
2. From `backend/`, create a virtual environment (recommended): `python -m venv venv`, then activate it (`venv\Scripts\activate` on Windows, `source venv/bin/activate` on macOS/Linux).
3. Install dependencies: `pip install -r backend/requirements.txt`.
4. Copy `.env.example` to `.env` at the repository root and fill in your own values — never commit the real `.env`.
5. Provide your own Supabase project's `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env`.
6. Apply the SQL files in `supabase/migrations/` to your Supabase project, in filename order (`20260825000000_initial_schema.sql` then `20260826000000_human_reviews.sql`), via the Supabase SQL editor or CLI, so the required tables exist.
7. Start the backend from the `backend/` directory: `uvicorn main:app --reload` (imports in this codebase are unqualified relative to `backend/`, so `uvicorn` must be run with `backend/` as the working directory — running it from the repository root will fail to import).
8. Open `http://127.0.0.1:8000/` in a browser. The frontend is served as static files by this same FastAPI process (`backend/main.py` mounts `frontend/` at `/`) — there is no separate frontend server or build step to run.

If `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` are not set, the backend still starts; `GET /api/health` reports the database as `not_configured` and persistence-backed endpoints return a `503`.

## API

All routes are served under the `/api` prefix.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Application and database health |
| GET | `/api/cases` | List cases (Command Center summary) |
| GET | `/api/cases/{case_id}` | Full case + run detail (optional `?run_id=`) |
| GET | `/api/cases/{case_id}/runs` | List every run for a case |
| GET | `/api/cases/{case_id}/decision` | GOVERN decision detail for a run |
| GET | `/api/cases/{case_id}/evidence` | Agent positions, conflict, RESOLVE candidates, WEIGH result |
| GET | `/api/cases/{case_id}/timeline` | Audit trail + human reviews for a run |
| POST | `/api/cases/{case_id}/run` | Run the real pipeline for a case (raw agent evidence in, full outcome out) |
| POST | `/api/cases/{case_id}/review` | Record a human reviewer's annotation (approve/reject/request_more_evidence) |
| GET | `/api/scenarios` | List Scenario Lab scenarios |
| POST | `/api/scenarios/{scenario_id}/run` | Run a Scenario Lab scenario through the real pipeline |
| GET | `/api/system/reliability` | Aggregate reliability metrics over persisted runs |

`case_id` accepts either the internal case id or the caller's own `external_case_id`. `run_id` is a query parameter accepted where relevant; omitting it defaults to a case's latest run.

## Testing

```
pytest -q
```

Run from the `backend/` directory (or anywhere with `backend/` on `PYTHONPATH`, as `pytest.ini` already configures). As of commit `7111ff9`, this reports **640 passed** — treat that number as a snapshot at that commit, not a guarantee for later changes; re-run the command to get the current count.

## Security

- `.env` is listed in `.gitignore` and must never be committed.
- `SUPABASE_SERVICE_ROLE_KEY` is read only server-side (`backend/persistence/connection.py`) and is never sent to, or embedded in, the frontend.
- The frontend (`frontend/index.html`, `app.js`, `agent_fields.js`, `styles.css`) contains no Supabase URL, key, or other credential — it only calls this backend's own `/api/*` routes.
- Do not commit real credentials anywhere in this repository, including in tests or example files — `.env.example` (below) contains variable names only.

## Demo / fallback status

The Scenario Lab described above **is** the current safe demo path: fully deterministic, backed by the real pipeline, and requiring no external LLM or API beyond your own Supabase project. There is currently no separate "external API unavailable" fallback mechanism in this repository beyond that — none has been built, and this document does not claim otherwise.
