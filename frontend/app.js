// Sentinel demo UI. Talks only to the existing FastAPI backend (same origin,
// relative /api/* paths) -- never to Supabase directly, and never contains a
// Supabase URL, anon key, or service-role key. Every value shown for
// RESOLVE/WEIGH/GOVERN/EXECUTOR is rendered verbatim from the API response;
// nothing here recalculates a score, a rank, or an authorization decision.

const API_BASE = "/api";

// Known historical connectivity-verification artifacts, not demo data --
// created directly against PersistenceStore outside the API by an earlier
// verification pass, before the Scenario Lab or this UI existed. Named
// explicitly by their stable external_case_id (never an internal UUID,
// which is environment-specific) rather than by a naming-convention guess
// (e.g. "doesn't start with scenario-"), so no legitimate case is ever
// excluded by accident. This hides them from the judge-facing case list
// only -- GET /api/cases itself stays a complete, truthful read of every
// persisted case; nothing in Supabase is touched, updated, or deleted.
const HIDDEN_EXTERNAL_CASE_IDS = new Set([
  "sentinel-live-verify-001",
  "sentinel-live-verify-rejected-001",
  "sentinel-live-verify-failed-001",
]);

const state = {
  cases: [],
  scenarios: [],
  selectedCaseId: null,
  selectedRunId: null, // null = latest run
  activeTab: "agents",
};

// -- tiny helpers -------------------------------------------------------

function esc(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function fmtTime(iso) {
  if (!iso) return "--";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function fmtNum(n, digits = 3) {
  if (n === null || n === undefined) return "--";
  const num = Number(n);
  return Number.isFinite(num) ? num.toFixed(digits) : String(n);
}

function badge(text, tone) {
  return `<span class="badge badge--${esc(tone)}">${esc(text)}</span>`;
}

// GOVERN outcomes are exactly PROCEED/HOLD/ESCALATE/AMBIGUOUS (the schema's
// own check constraint); EXECUTOR receipt status is exactly EXECUTED/REJECTED.
// No other value is ever invented here.
function outcomeTone(outcome) {
  switch (outcome) {
    case "PROCEED":
      return "good";
    case "HOLD":
      return "warn";
    case "ESCALATE":
      return "bad";
    case "AMBIGUOUS":
      return "info";
    case "FAILED":
      return "bad";
    default:
      return "neutral";
  }
}

function receiptTone(status) {
  if (status === "EXECUTED") return "good";
  if (status === "REJECTED") return "bad";
  return "neutral";
}

function jsonBlock(value) {
  if (value === null || value === undefined) return '<p class="muted">--</p>';
  return `<pre class="json-block">${esc(JSON.stringify(value, null, 2))}</pre>`;
}

// -- API layer ------------------------------------------------------------

class ApiError extends Error {
  constructor(status, body) {
    super(`API error ${status}`);
    this.status = status;
    this.body = body;
  }
}

async function apiGet(path) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { headers: { Accept: "application/json" } });
  } catch (networkErr) {
    throw new ApiError(0, null);
  }
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  if (!response.ok) throw new ApiError(response.status, body);
  return body;
}

async function apiPost(path, payload) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (networkErr) {
    throw new ApiError(0, null);
  }
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  if (!response.ok) throw new ApiError(response.status, body);
  return body;
}

function errorMessage(err) {
  if (!(err instanceof ApiError)) return "Unexpected client-side error.";
  const detail = err.body && err.body.error && err.body.error.message;
  switch (err.status) {
    case 0:
      return "Cannot reach the Sentinel API. Is the backend running?";
    case 404:
      return detail || "Not found.";
    case 422:
      return detail || "The request failed validation.";
    case 503:
      return detail || "The backend/database is unavailable right now.";
    case 500:
    case 502:
      return detail || "The server hit an unexpected error.";
    default:
      return detail || `Request failed (HTTP ${err.status}).`;
  }
}

function renderErrorPanel(container, err) {
  const status = err instanceof ApiError ? err.status : "--";
  container.innerHTML = `
    <div class="error-box">
      <strong>Couldn't load this section</strong> (HTTP ${esc(status)})
      <p>${esc(errorMessage(err))}</p>
    </div>`;
}

// -- health ----------------------------------------------------------------

async function refreshHealth() {
  const el = document.getElementById("health");
  try {
    const body = await apiGet("/health");
    const dbStatus = body.application && body.database ? body.database.status : "unknown";
    if (dbStatus === "ok") {
      el.className = "health health--ok";
      el.textContent = "backend + database: ok";
    } else if (dbStatus === "not_configured") {
      el.className = "health health--warn";
      el.textContent = "backend up, Supabase not configured";
    } else {
      el.className = "health health--bad";
      el.textContent = `backend up, database: ${dbStatus}`;
    }
  } catch (err) {
    el.className = "health health--bad";
    el.textContent = "backend unreachable";
  }
}

// -- case list ---------------------------------------------------------------

function caseSummaryLine(c) {
  const parts = [];
  if (c.status) parts.push(badge(c.status, outcomeTone(c.status)));
  if (c.outcome) parts.push(badge(c.outcome, outcomeTone(c.outcome)));
  if (c.human_review_required) parts.push(badge("needs review", "warn"));
  return parts.join(" ");
}

async function loadCases() {
  const container = document.getElementById("case-list");
  try {
    state.cases = await apiGet("/cases");
  } catch (err) {
    renderErrorPanel(container, err);
    return;
  }
  // Presentation-only filter: GET /api/cases above already returned every
  // persisted case, untouched -- this only decides what the judge-facing
  // list renders.
  const visibleCases = state.cases.filter((c) => !HIDDEN_EXTERNAL_CASE_IDS.has(c.external_case_id));
  if (visibleCases.length === 0) {
    container.innerHTML = '<p class="muted">No cases yet -- run a demo scenario or submit one.</p>';
    return;
  }
  container.innerHTML = visibleCases
    .map((c) => {
      const title = esc(c.external_case_id || c.case_id);
      const selected = c.case_id === state.selectedCaseId ? " case-item--active" : "";
      return `
        <button class="case-item${selected}" data-case-id="${esc(c.case_id)}">
          <div class="case-item-title">${title}</div>
          <div class="case-item-meta">${caseSummaryLine(c)}</div>
          <div class="case-item-sub muted">runs: ${esc(c.run_count)} &middot; ${esc(fmtTime(c.latest_run_created_at))}</div>
        </button>`;
    })
    .join("");
  container.querySelectorAll(".case-item").forEach((btn) => {
    btn.addEventListener("click", () => selectCase(btn.dataset.caseId, null));
  });
}

// -- scenario lab (existing deterministic fallback/demo mode) ----------------

async function loadScenarios() {
  const container = document.getElementById("scenario-list");
  try {
    state.scenarios = await apiGet("/scenarios");
  } catch (err) {
    renderErrorPanel(container, err);
    return;
  }
  container.innerHTML = state.scenarios
    .map(
      (s) => `
        <button class="scenario-item" data-scenario-id="${esc(s.id)}" title="${esc(s.description)}">
          &#9654; ${esc(s.title)}
        </button>`
    )
    .join("");
  container.querySelectorAll(".scenario-item").forEach((btn) => {
    btn.addEventListener("click", () => runScenario(btn.dataset.scenarioId, btn));
  });
}

async function runScenario(scenarioId, btn) {
  btn.disabled = true;
  const original = btn.textContent;
  btn.textContent = "Running...";
  try {
    const outcome = await apiPost(`/scenarios/${encodeURIComponent(scenarioId)}/run`, {});
    await loadCases();
    selectCase(outcome.case_id, outcome.case_run_id);
  } catch (err) {
    alert(errorMessage(err));
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
}

// -- new case form -------------------------------------------------------------

function buildAgentFieldset(role) {
  const fieldset = document.querySelector(`.agent-fieldset[data-role="${role}"] .agent-fields`);
  const typeOptions = Object.entries(AGENT_TYPES)
    .map(([key, def]) => `<option value="${esc(key)}">${esc(def.label)}</option>`)
    .join("");

  fieldset.innerHTML = `
    <label>
      Agent type
      <select class="agent-type">${typeOptions}</select>
    </label>
    <label>
      Proposed action
      <select class="agent-action"></select>
    </label>
    <label>
      Confidence (0-1)
      <input type="number" class="agent-confidence" min="0" max="1" step="0.01" required />
    </label>
    <div class="agent-domain-fields"></div>
  `;

  const typeSelect = fieldset.querySelector(".agent-type");
  const renderForType = () => renderAgentTypeFields(fieldset, typeSelect.value);
  typeSelect.addEventListener("change", renderForType);
  // default: agent_a starts as payouts, agent_b as dispute, to mirror the
  // documented payout-vs-dispute conflict pair out of the box.
  typeSelect.value = role === "agent_a" ? "payouts" : "dispute";
  renderForType();
}

function renderAgentTypeFields(fieldset, agentTypeKey) {
  const def = AGENT_TYPES[agentTypeKey];
  const actionSelect = fieldset.querySelector(".agent-action");
  actionSelect.innerHTML = def.actions.map((a) => `<option value="${esc(a)}">${esc(a)}</option>`).join("");

  const confidenceInput = fieldset.querySelector(".agent-confidence");
  confidenceInput.value = def.defaultConfidence;

  const domainContainer = fieldset.querySelector(".agent-domain-fields");
  domainContainer.innerHTML = def.fields
    .map((f) => {
      if (f.type === "select") {
        const opts = f.options.map((o) => `<option value="${esc(o)}">${esc(o)}</option>`).join("");
        return `<label>${esc(f.label)}<select data-field="${esc(f.name)}">${opts}</select></label>`;
      }
      return `<label>${esc(f.label)}<input type="${esc(f.type)}" step="${esc(f.step || "any")}" data-field="${esc(
        f.name
      )}" placeholder="${esc(f.placeholder || "")}" /></label>`;
    })
    .join("");
}

function readAgentFieldset(role) {
  const fieldset = document.querySelector(`.agent-fieldset[data-role="${role}"]`);
  const agentTypeKey = fieldset.querySelector(".agent-type").value;
  const def = AGENT_TYPES[agentTypeKey];
  const payload = {
    agent: agentTypeKey,
    proposed_action: fieldset.querySelector(".agent-action").value,
    confidence: parseFloat(fieldset.querySelector(".agent-confidence").value),
  };
  def.fields.forEach((f) => {
    const input = fieldset.querySelector(`[data-field="${f.name}"]`);
    if (!input || input.value === "") return;
    payload[f.name] = f.type === "number" ? parseFloat(input.value) : input.value;
  });
  return payload;
}

function openNewCasePanel() {
  document.getElementById("new-case-panel").classList.remove("hidden");
  document.getElementById("empty-state").classList.add("hidden");
  document.getElementById("case-detail").classList.add("hidden");
}

function closeNewCasePanel() {
  document.getElementById("new-case-panel").classList.add("hidden");
  if (state.selectedCaseId) {
    document.getElementById("case-detail").classList.remove("hidden");
  } else {
    document.getElementById("empty-state").classList.remove("hidden");
  }
}

async function submitNewCase(event) {
  event.preventDefault();
  const form = event.target;
  const errorBox = document.getElementById("new-case-error");
  errorBox.classList.add("hidden");

  const externalIdInput = form.elements["external_case_id"].value.trim();
  const externalCaseId = externalIdInput || `case-${Date.now()}`;
  const entityType = form.elements["entity_type"].value;
  const contextId = form.elements["context_id"].value.trim();

  const payload = {
    entity_type: entityType,
    agent_a: readAgentFieldset("agent_a"),
    agent_b: readAgentFieldset("agent_b"),
  };
  if (contextId) {
    payload.case_context = { case_id: externalCaseId, merchant_id: contextId };
  }

  const submitBtn = form.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  submitBtn.textContent = "Running pipeline...";

  try {
    const outcome = await apiPost(`/cases/${encodeURIComponent(externalCaseId)}/run`, payload);
    closeNewCasePanel();
    await loadCases();
    selectCase(outcome.case_id, outcome.case_run_id);
  } catch (err) {
    errorBox.textContent = errorMessage(err);
    errorBox.classList.remove("hidden");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Run case through Sentinel";
  }
}

// -- case detail: overview -----------------------------------------------------

async function selectCase(caseId, runId) {
  state.selectedCaseId = caseId;
  state.selectedRunId = runId;
  document.getElementById("new-case-panel").classList.add("hidden");
  document.getElementById("empty-state").classList.add("hidden");
  document.getElementById("case-detail").classList.remove("hidden");

  document.querySelectorAll(".case-item").forEach((btn) => {
    btn.classList.toggle("case-item--active", btn.dataset.caseId === caseId);
  });

  await renderOverview();
  await loadActiveTab();
}

function runQuery() {
  return state.selectedRunId ? `?run_id=${encodeURIComponent(state.selectedRunId)}` : "";
}

async function renderOverview() {
  const container = document.getElementById("case-overview");
  container.innerHTML = '<p class="muted">Loading case overview&hellip;</p>';
  let detail;
  try {
    detail = await apiGet(`/cases/${encodeURIComponent(state.selectedCaseId)}${runQuery()}`);
  } catch (err) {
    renderErrorPanel(container, err);
    return;
  }

  const run = detail.run;
  const govern = detail.govern_result;
  const receipt = detail.execution_receipt;

  if (!run) {
    container.innerHTML = `
      <div class="overview-grid">
        <div><span class="label">Case ID</span><div>${esc(detail.case.id)}</div></div>
        <div><span class="label">External ID</span><div>${esc(detail.case.external_case_id || "--")}</div></div>
        <div><span class="label">Created</span><div>${esc(fmtTime(detail.case.created_at))}</div></div>
      </div>
      <p class="muted">This case has no runs yet.</p>`;
    return;
  }

  container.innerHTML = `
    <div class="overview-grid">
      <div><span class="label">Case ID</span><div>${esc(detail.case.id)}</div></div>
      <div><span class="label">External ID</span><div>${esc(detail.case.external_case_id || "--")}</div></div>
      <div><span class="label">Run ID</span><div>${esc(run.id)}</div></div>
      <div><span class="label">Status</span><div>${badge(run.status, outcomeTone(run.status))}</div></div>
      <div><span class="label">Outcome</span><div>${govern ? badge(govern.outcome, outcomeTone(govern.outcome)) : '<span class="muted">--</span>'}</div></div>
      <div><span class="label">Executed</span><div>${receipt ? badge(receipt.status, receiptTone(receipt.status)) : '<span class="muted">--</span>'}</div></div>
      <div><span class="label">Entity type</span><div>${esc(run.entity_type)}</div></div>
      <div><span class="label">Run created</span><div>${esc(fmtTime(run.created_at))}</div></div>
    </div>`;
}

// -- tabs -----------------------------------------------------------------------

function initTabs() {
  document.querySelectorAll(".tab").forEach((tabBtn) => {
    tabBtn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      tabBtn.classList.add("active");
      document.querySelector(`.tab-panel[data-tab="${tabBtn.dataset.tab}"]`).classList.add("active");
      state.activeTab = tabBtn.dataset.tab;
      loadActiveTab();
    });
  });
}

function loadActiveTab() {
  if (!state.selectedCaseId) return Promise.resolve();
  const loaders = {
    agents: loadAgentsTab,
    resolve: loadResolveTab,
    weigh: loadWeighTab,
    govern: loadGovernTab,
    executor: loadExecutorTab,
    audit: loadAuditTab,
    history: loadHistoryTab,
  };
  return loaders[state.activeTab]();
}

// C. Agent disagreement -----------------------------------------------------

async function loadAgentsTab() {
  const container = document.getElementById("panel-agents");
  container.innerHTML = '<p class="muted">Loading agents &amp; conflict&hellip;</p>';
  let evidence;
  try {
    evidence = await apiGet(`/cases/${encodeURIComponent(state.selectedCaseId)}/evidence${runQuery()}`);
  } catch (err) {
    renderErrorPanel(container, err);
    return;
  }

  const agents = evidence.agents || [];
  const conflict = evidence.conflict;

  const agentCards = agents
    .map(
      (a) => `
      <div class="agent-card">
        <div class="agent-card-header">
          <strong>${esc(a.agent_name)}</strong>
          <span class="role-tag">${esc(a.role)}</span>
        </div>
        <div><span class="label">Proposed action</span><div>${esc(a.proposed_action)}</div></div>
        <div><span class="label">Confidence</span><div>${fmtNum(a.confidence)}</div></div>
        ${jsonBlock(a.payload)}
      </div>`
    )
    .join("");

  container.innerHTML = `
    <h3>Agent positions</h3>
    <div class="agent-grid">${agentCards || '<p class="muted">No agent outputs recorded.</p>'}</div>

    <h3>Conflict</h3>
    ${
      conflict
        ? `
      <div class="conflict-box conflict-box--${conflict.conflict ? "yes" : "no"}">
        <div>${badge(conflict.conflict ? "CONFLICT" : "NO CONFLICT", conflict.conflict ? "bad" : "good")}</div>
        <div><span class="label">Action A</span> ${esc(conflict.action_a)} &nbsp; vs &nbsp; <span class="label">Action B</span> ${esc(conflict.action_b)}</div>
        <div><span class="label">Reason</span><div>${esc(conflict.reason)}</div></div>
      </div>`
        : '<p class="muted">No conflict record for this run.</p>'
    }`;
}

// D + E. Resolve + Weigh -----------------------------------------------------

function strategyTone(strategy) {
  if (strategy === "SUPPRESS_ACTION") return "bad";
  if (strategy === "HOLD_BOTH_PENDING_REVIEW") return "warn";
  return "neutral";
}

async function loadResolveTab() {
  const container = document.getElementById("panel-resolve");
  container.innerHTML = '<p class="muted">Loading candidates&hellip;</p>';
  let evidence;
  try {
    evidence = await apiGet(`/cases/${encodeURIComponent(state.selectedCaseId)}/evidence${runQuery()}`);
  } catch (err) {
    renderErrorPanel(container, err);
    return;
  }

  const candidates = evidence.candidates || [];
  if (candidates.length === 0) {
    container.innerHTML = '<p class="muted">RESOLVE produced no candidates for this run.</p>';
    return;
  }

  container.innerHTML = `
    <h3>RESOLVE candidates (as persisted -- not recalculated here)</h3>
    <div class="candidate-grid">
      ${candidates
        .map(
          (c) => `
        <div class="candidate-card">
          <div class="candidate-card-header">
            <span>${esc(c.candidate_id)}</span>
            ${badge(c.strategy, strategyTone(c.strategy))}
          </div>
          <div><span class="label">Preferred agent</span><div>${esc(c.preferred_agent || "--")}</div></div>
          <div><span class="label">Resulting actions</span><div>${esc((c.resulting_actions || []).join(", ") || "--")}</div></div>
          <div><span class="label">Rationale</span><div>${esc(c.rationale)}</div></div>
          <div><span class="label">Source rule</span><div>${esc(c.source_rule)}</div></div>
        </div>`
        )
        .join("")}
    </div>`;
}

async function loadWeighTab() {
  const container = document.getElementById("panel-weigh");
  container.innerHTML = '<p class="muted">Loading WEIGH result&hellip;</p>';
  let evidence;
  try {
    evidence = await apiGet(`/cases/${encodeURIComponent(state.selectedCaseId)}/evidence${runQuery()}`);
  } catch (err) {
    renderErrorPanel(container, err);
    return;
  }

  const weigh = evidence.weigh_result;
  const candidates = (evidence.candidates || []).slice().sort((a, b) => {
    const rankA = a.score ? a.score.rank : Infinity;
    const rankB = b.score ? b.score.rank : Infinity;
    return rankA - rankB;
  });

  if (!weigh) {
    container.innerHTML = '<p class="muted">WEIGH did not produce a result for this run.</p>';
    return;
  }

  const scoreRows = candidates
    .map((c) => {
      const s = c.score;
      if (!s) return `<tr><td>${esc(c.candidate_id)}</td><td colspan="6" class="muted">not scored</td></tr>`;
      return `
        <tr>
          <td>${esc(c.candidate_id)}</td>
          <td>${esc(s.rank)}</td>
          <td>${fmtNum(s.total_score, 4)}</td>
          <td>${badge(s.eligible ? "eligible" : "ineligible", s.eligible ? "good" : "bad")}</td>
          <td>${esc(s.eligibility_basis)}</td>
          <td>${esc(s.originating_agent || "--")}</td>
          <td>${fmtNum(s.originating_confidence)}</td>
        </tr>`;
    })
    .join("");

  container.innerHTML = `
    <h3>Ranking &amp; scores</h3>
    <table class="score-table">
      <thead>
        <tr><th>Candidate</th><th>Rank</th><th>Total score</th><th>Eligible</th><th>Basis</th><th>Originating agent</th><th>Origin. confidence</th></tr>
      </thead>
      <tbody>${scoreRows}</tbody>
    </table>

    <div class="weigh-grid">
      <div>
        <h4>Profile &amp; confidence</h4>
        <div><span class="label">Profile</span><div>${esc(weigh.profile_name)} (${esc(weigh.profile_reason)})</div></div>
        <div><span class="label">Case confidence</span><div>${fmtNum(weigh.case_confidence)} via ${esc(weigh.confidence_method)}</div></div>
        <div><span class="label">Evidence complete</span><div>${badge(weigh.evidence_complete ? "yes" : "no", weigh.evidence_complete ? "good" : "warn")}</div></div>
      </div>
      <div>
        <h4>Ambiguity</h4>
        <div><span class="label">Detected</span><div>${badge(weigh.ambiguity_detected ? "yes" : "no", weigh.ambiguity_detected ? "warn" : "good")}</div></div>
        <div><span class="label">Near-tie group</span><div>${esc((weigh.near_tie_group || []).join(", ") || "--")}</div></div>
        <div><span class="label">Top gap</span><div>${fmtNum(weigh.top_gap, 4)}</div></div>
        ${jsonBlock(weigh.ambiguity_signals)}
      </div>
    </div>

    <h4>Weights used</h4>
    ${jsonBlock(weigh.weights_used)}

    <h4>Candidate objective impacts &amp; constraint findings</h4>
    <div class="candidate-grid">
      ${candidates
        .map(
          (c) => `
        <div class="candidate-card">
          <div class="candidate-card-header"><span>${esc(c.candidate_id)}</span></div>
          <h5>Objective impacts</h5>
          ${jsonBlock(c.score ? c.score.objective_impacts : null)}
          <h5>Constraint findings</h5>
          ${jsonBlock(c.score ? c.score.constraint_findings : null)}
        </div>`
        )
        .join("")}
    </div>

    <h4>Constraint evaluation (run-level)</h4>
    ${jsonBlock(weigh.constraint_evaluation)}`;
}

// F. Govern -----------------------------------------------------------------

async function loadGovernTab() {
  const container = document.getElementById("panel-govern");
  container.innerHTML = '<p class="muted">Loading GOVERN decision&hellip;</p>';
  let decision;
  try {
    decision = await apiGet(`/cases/${encodeURIComponent(state.selectedCaseId)}/decision${runQuery()}`);
  } catch (err) {
    renderErrorPanel(container, err);
    return;
  }

  if (!decision.govern_result) {
    container.innerHTML = `<p class="muted">${esc(decision.note || "GOVERN has not produced a result for this run.")}</p>`;
    return;
  }

  container.innerHTML = `
    <div class="govern-headline govern-headline--${outcomeTone(decision.outcome)}">
      <div class="govern-outcome">${badge(decision.outcome, outcomeTone(decision.outcome))}</div>
      <div><span class="label">Execution authorized</span> ${badge(decision.execution_authorized ? "YES" : "NO", decision.execution_authorized ? "good" : "bad")}</div>
      <div><span class="label">Outcome basis</span><div>${esc(decision.outcome_basis)}</div></div>
    </div>

    <div class="overview-grid">
      <div><span class="label">Decision ID</span><div>${esc(decision.decision_id)}</div></div>
      <div><span class="label">Profile selected</span><div>${esc(decision.profile_selected)}</div></div>
      <div><span class="label">Policy hash</span><div class="mono-small">${esc(decision.policy_hash)}</div></div>
      <div><span class="label">Objectives considered</span><div>${esc((decision.objectives_considered || []).join(", "))}</div></div>
    </div>

    <div class="govern-candidates">
      <div>
        <h4>Selected candidate</h4>
        ${decision.selected_candidate ? candidateSummaryBlock(decision.selected_candidate) : '<p class="muted">None selected.</p>'}
      </div>
      <div>
        <h4>Candidate under review</h4>
        ${decision.candidate_under_review ? candidateSummaryBlock(decision.candidate_under_review) : '<p class="muted">None.</p>'}
      </div>
    </div>

    <h4>Authorized actions</h4>
    ${jsonBlock(decision.authorized_actions)}

    <h4>Score band</h4>
    ${jsonBlock(decision.score_band)}

    <h4>Permission evaluation</h4>
    ${jsonBlock(decision.permission_evaluation)}

    <h4>Escalation</h4>
    ${jsonBlock(decision.escalation)}

    <h4>Rationale</h4>
    ${jsonBlock(decision.rationale)}`;
}

function candidateSummaryBlock(candidate) {
  return `
    <div class="candidate-card">
      <div class="candidate-card-header"><span>${esc(candidate.candidate_id)}</span>${badge(candidate.strategy, strategyTone(candidate.strategy))}</div>
      <div><span class="label">Resulting actions</span><div>${esc((candidate.resulting_actions || []).join(", ") || "--")}</div></div>
      <div><span class="label">Rationale</span><div>${esc(candidate.rationale)}</div></div>
    </div>`;
}

// G. Executor ------------------------------------------------------------------

async function loadExecutorTab() {
  const container = document.getElementById("panel-executor");
  container.innerHTML = '<p class="muted">Loading EXECUTOR receipt&hellip;</p>';
  let detail;
  try {
    detail = await apiGet(`/cases/${encodeURIComponent(state.selectedCaseId)}${runQuery()}`);
  } catch (err) {
    renderErrorPanel(container, err);
    return;
  }

  const receipt = detail.execution_receipt;
  if (!receipt) {
    container.innerHTML = '<p class="muted">EXECUTOR has not produced a receipt for this run (GOVERN may not have authorized execution, or the run has not reached EXECUTOR yet).</p>';
    return;
  }

  container.innerHTML = `
    <div class="govern-headline govern-headline--${receiptTone(receipt.status)}">
      <div>${badge(receipt.status, receiptTone(receipt.status))}</div>
      <div><span class="label">Execution mode</span><div>${esc(receipt.execution_mode)}</div></div>
      <div><span class="label">Receipt ID</span><div class="mono-small">${esc(receipt.receipt_id)}</div></div>
    </div>

    <h4>Executed actions</h4>
    ${jsonBlock(receipt.executed_actions)}

    ${
      receipt.status === "REJECTED"
        ? `<h4>Rejection</h4>${jsonBlock(receipt.rejection)}`
        : ""
    }

    <h4>Authorization block</h4>
    ${jsonBlock(receipt.authorization)}

    <h4>Authorization checks (ladder trail)</h4>
    ${jsonBlock(receipt.authorization_checks)}`;
}

// H. Audit timeline --------------------------------------------------------------

function stageTone(outcome) {
  return outcome === "SUCCEEDED" ? "good" : "bad";
}

async function loadAuditTab() {
  const container = document.getElementById("panel-audit");
  container.innerHTML = '<p class="muted">Loading audit timeline&hellip;</p>';
  let timeline;
  try {
    timeline = await apiGet(`/cases/${encodeURIComponent(state.selectedCaseId)}/timeline${runQuery()}`);
  } catch (err) {
    renderErrorPanel(container, err);
    return;
  }

  const events = timeline.events || [];
  const reviews = timeline.human_reviews || [];

  container.innerHTML = `
    <h3>Audit trail</h3>
    <ol class="timeline">
      ${events
        .map(
          (e) => `
        <li class="timeline-item timeline-item--${stageTone(e.outcome)}">
          <div class="timeline-stage">${esc(e.stage)} ${badge(e.outcome, stageTone(e.outcome))}</div>
          <div class="timeline-time muted">${esc(fmtTime(e.occurred_at))}</div>
          <div>${esc(e.summary)}</div>
          ${e.detail ? jsonBlock(e.detail) : ""}
        </li>`
        )
        .join("") || '<li class="muted">No audit events recorded.</li>'}
    </ol>

    <h3>Human reviews</h3>
    ${
      reviews.length
        ? `<div class="candidate-grid">${reviews
            .map(
              (r) => `
        <div class="candidate-card">
          <div class="candidate-card-header"><span>${esc(r.action)}</span></div>
          <div><span class="label">Reviewer</span><div>${esc(r.reviewer || "--")}</div></div>
          <div><span class="label">Reason</span><div>${esc(r.reason || "--")}</div></div>
          <div><span class="label">Status at review</span><div>${esc(r.case_run_status_at_review)}</div></div>
          <div><span class="label">Recorded</span><div>${esc(fmtTime(r.created_at))}</div></div>
        </div>`
            )
            .join("")}</div>`
        : '<p class="muted">No human review recorded for this run.</p>'
    }`;
}

// I. Run history -------------------------------------------------------------------

async function loadHistoryTab() {
  const container = document.getElementById("panel-history");
  container.innerHTML = '<p class="muted">Loading run history&hellip;</p>';
  let runs;
  try {
    runs = await apiGet(`/cases/${encodeURIComponent(state.selectedCaseId)}/runs`);
  } catch (err) {
    renderErrorPanel(container, err);
    return;
  }

  if (runs.length === 0) {
    container.innerHTML = '<p class="muted">No runs recorded for this case.</p>';
    return;
  }

  container.innerHTML = `
    <h3>All runs for this case (newest first)</h3>
    <div class="run-list">
      ${runs
        .map((r) => {
          const active = r.case_run_id === state.selectedRunId || (!state.selectedRunId && r === runs[0]);
          return `
          <button class="run-item${active ? " run-item--active" : ""}" data-run-id="${esc(r.case_run_id)}">
            <div>${badge(r.status, outcomeTone(r.status))} ${r.outcome ? badge(r.outcome, outcomeTone(r.outcome)) : ""} ${badge(r.executed ? "EXECUTED" : "NOT EXECUTED", r.executed ? "good" : "neutral")}</div>
            <div class="muted">${esc(r.case_run_id)}</div>
            <div class="muted">${esc(fmtTime(r.created_at))}</div>
          </button>`;
        })
        .join("")}
    </div>`;

  container.querySelectorAll(".run-item").forEach((btn) => {
    btn.addEventListener("click", async () => {
      state.selectedRunId = btn.dataset.runId;
      await renderOverview();
      const stayOnTab = state.activeTab;
      await loadActiveTab();
      state.activeTab = stayOnTab;
    });
  });
}

// -- wire-up ---------------------------------------------------------------------

function init() {
  refreshHealth();
  loadCases();
  loadScenarios();
  initTabs();

  document.getElementById("refresh-cases").addEventListener("click", loadCases);
  document.getElementById("open-new-case").addEventListener("click", () => {
    openNewCasePanel();
    buildAgentFieldset("agent_a");
    buildAgentFieldset("agent_b");
  });
  document.getElementById("close-new-case").addEventListener("click", closeNewCasePanel);
  document.getElementById("new-case-form").addEventListener("submit", submitNewCase);
}

document.addEventListener("DOMContentLoaded", init);
