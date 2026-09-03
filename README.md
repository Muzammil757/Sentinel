# Sentinel

**TL;DR:** Sentinel is a fail-closed governance layer that lets multiple
autonomous AI agents propose conflicting actions, then deterministically
decides what they're actually allowed to do — authorizing, blocking, or
escalating each case, with a full audit trail. One scenario runs on real,
live Gemini-powered agents to prove the governance layer is genuinely
agent-agnostic.

Sentinel is a governance/decision pipeline for resolving conflicting recommendations from multiple autonomous agents. When two (or more) agents propose actions that disagree — e.g. a Payouts agent wants to release a payment while a Dispute agent wants to hold related actions — Sentinel deterministically detects the conflict, generates candidate resolutions, scores them against policy, authorizes (or blocks/escalates) a decision, and executes it under a fail-closed authorization boundary. Every stage of that process is persisted for full auditability.

Built for the Razorpay Buildathon as a demonstration of policy-driven, auditable multi-agent governance — not a live payments integration. Six of the seven demo scenarios use fixed agent evidence defined directly in `backend/api/scenarios.py` (the standalone generator functions in `backend/mock_agents/` exist in the codebase but are not currently wired into the Scenario Lab). The seventh scenario uses two real Gemini-powered agents that generate their proposals live. Execution is always a recorded mock effect in every scenario — never a real payment or account action.

## Where AI fits

Sentinel governs autonomous AI agents' proposed actions — it doesn't replace or simulate the agents' intelligence itself. Six of the seven demo scenarios use fixed, deterministic agent evidence so those outcomes are exactly reproducible for judges, with zero external API cost or latency.

The seventh scenario (`scenario-live-ai-agent`) uses two real Gemini-powered agents that genuinely reason over case details and choose their own proposed action from a bounded set — not scripted, not pre-written. Their live output flows through the exact same unmodified governance pipeline as every other case: Conflict Matrix, RESOLVE, WEIGH, GOVERN, EXECUTOR all treat a real AI agent's proposal identically to a deterministic one. This is the proof that Sentinel's governance layer is genuinely agent-agnostic, not a claim.

If the live API call fails or times out, the system falls back to a real, previously-captured response rather than breaking — so a demo never shows an error, even if the model call has a bad moment.

GOVERN's own advisor port (`backend/govern/advisor.py`) remains a separate, still-unwired extension point — designed for GOVERN to optionally *consult* an LLM without ever letting it authorize an action. That boundary is deliberate: agents may be powered by AI, but authorization never is.

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

All decision-making happens in the Python backend (`backend/conflict_matrix/`, `backend/resolve/`, `backend/weigh/`, `backend/govern/`, `backend/executor/`). Supabase is persistence, audit-trail, and read-model infrastructure only — it stores what the pipeline decided and lets the API read it back; it never makes, re-derives, or influences a decision. No decision logic exists in the API layer, the frontend, or in Supabase (no scoring/authorization triggers or functions). This holds for every scenario, including the live-AI one — only the *source* of the initial agent proposals differs; everything downstream is identical code.

## How a decision works

1. **Agents** each propose an action from their own narrow view of a case (e.g. Payouts proposes `RELEASE_PAYMENT`, Dispute proposes `HOLD_RELATED_ACTIONS`). In six scenarios this evidence is fixed; in `scenario-live-ai-agent`, two agents generate it live via the Gemini API.
2. **Conflict Matrix** deterministically checks whether the two proposed actions conflict for the given entity type.
3. **RESOLVE** generates candidate resolutions (e.g. defer to one agent, or hold both pending review) for the pipeline to evaluate.
4. **WEIGH** scores every candidate against the active policy — objective weights, hard-constraint checks, confidence, and ambiguity detection — producing a ranked, eligibility-annotated result.
5. **GOVERN** is the sole authorization boundary: it re-checks constraints, applies authority limits, and decides the case outcome (`PROCEED`, `HOLD`, `ESCALATE`, or `AMBIGUOUS`), setting `execution_authorized` accordingly.
6. **EXECUTOR** obeys GOVERN and nothing else. It is fail-closed: a receipt is `EXECUTED` only if every check in its authorization ladder passes; anything else — including any internal error — produces a `REJECTED` receipt, never a silent success and never a raised exception that skips a record.
7. **Persistence** writes every stage's output (agents, conflict, candidates, scores, WEIGH result, GOVERN result, execution receipt, audit events) to Supabase, verbatim, as it happens — nothing here re-scores or re-decides anything.

## Demo scenarios (Scenario Lab)

`backend/api/scenarios.py` defines seven demo cases. Six use fixed, deterministic agent evidence (normal payout, agent disagreement held for review, authority-cap escalation, an ambiguous near-tie, an executor rejection, and a deliberate pipeline failure). The seventh, `scenario-live-ai-agent`, uses two agents whose proposals are generated live by the Gemini API. Every scenario — including the live one — runs through the exact same real pipeline a live case would (`POST /api/cases/{case_id}/run` or `POST /api/scenarios/{scenario_id}/run` under the hood); nothing about a scenario's outcome is hard-coded, and the pipeline decides it fresh every run.

**The six fixed scenarios** call no external LLM or third-party API and consume no external API credits. GOVERN's optional advisor port (`backend/govern/advisor.py`) defaults to `None`, documented in that module as "the demo-safe path: with no advisor, GOVERN is pure deterministic arithmetic over policy data and no model is involved" — nothing in this repository wires a real advisor into it.

**`scenario-live-ai-agent`** is the exception: two agents call the Gemini API (`gemini-2.5-flash`) with a constrained response schema, each genuinely choosing between two possible actions based on real case details rather than following a script. The returned action is validated against the allowed set; if the API call fails, times out, or returns something invalid, the code falls back to a real response captured from an earlier successful call — the demo never crashes or shows an error, live or otherwise. The only network calls anywhere in the Scenario Lab are to your own configured Supabase project, plus, for this one scenario, the Gemini API.

## Real Supabase

Sentinel persists every pipeline run to a Supabase/PostgreSQL project (`supabase/migrations/`). The backend needs exactly two environment variables:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Only the names are documented here — never their values (see `.env.example`). The service-role key is read only by `backend/persistence/connection.py`, server-side, and must never be exposed to the frontend. The frontend (`frontend/`) never contains a Supabase URL, key, or any other credential — it talks only to this backend's own `/api/*` endpoints, served same-origin.

## Live AI (Gemini)

The live-AI scenario (`scenario-live-ai-agent`) needs one additional environment variable:

- `GEMINI_API_KEY`

Read the same way as the Supabase credentials — server-side only, sent solely as a request header (`x-goog-api-key`), never as a URL parameter and never logged. If this variable is missing, invalid, or the API call otherwise fails, that one scenario automatically falls back to a real, previously-captured response rather than erroring. Every other scenario is entirely unaffected either way, since none of them call this API.

## Setup

1. Clone the repository.
2. From `backend/`, create a virtual environment (recommended): `python -m venv venv`, then activate it (`venv\Scripts\activate` on Windows, `source venv/bin/activate` on macOS/Linux).
3. Install dependencies: `pip install -r backend/requirements.txt`.
4. Copy `.env.example` to `.env` at the repository root and fill in your own values — never commit the real `.env`.
5. Provide your own Supabase project's `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env`. Optionally, add your own `GEMINI_API_KEY` (free, no card required, from aistudio.google.com) to enable the live-AI scenario — without it, that one scenario simply falls back to a saved response instead of calling the API live.
6. Apply the SQL files in `supabase/migrations/` to your Supabase project, in filename order (`20260825000000_initial_schema.sql` then `20260826000000_human_reviews.sql`), via the Supabase SQL editor or CLI, so the required tables exist.
7. Start the backend from the `backend/` directory: `uvicorn main:app --reload` (imports in this codebase are unqualified relative to `backend/`, so uvicorn must be run with `backend/` as the working directory — running it from the repository root will fail to import).
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

Run from the `backend/` directory (or anywhere with `backend/` on `PYTHONPATH`, as `pytest.ini` already configures). As of the latest commit, this suite reports 648 passed (644 from the core governance pipeline + 4 parametrized cases covering the two new action types added for the live-AI scenario) — treat that number as a snapshot, not a guarantee for later changes; re-run the command to get the current count.

## Security

- `.env` is listed in `.gitignore` and must never be committed.
- `SUPABASE_SERVICE_ROLE_KEY` and `GEMINI_API_KEY` are both read only server-side and are never sent to, or embedded in, the frontend.
- The frontend (`frontend/` — `index.html` plus its JSX components) contains no Supabase URL, key, Gemini key, or any other credential — it only calls this backend's own `/api/*` routes.
- Do not commit real credentials anywhere in this repository, including in tests or example files — `.env.example` (below) contains variable names only.

## Demo / fallback status

Six of the seven scenarios remain fully deterministic and require no external LLM or API beyond your own Supabase project — the original safe demo path is unchanged. The seventh (`scenario-live-ai-agent`) is the one exception: it calls the Gemini API live, and if that call fails, times out, or returns something outside the allowed action set, it falls back to a real, previously-captured response rather than erroring. This is a genuine fallback mechanism, scoped to this one scenario, because it's the only part of the system with a real external dependency.
