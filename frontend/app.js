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

// "agent_a" -> "Agent A" (the role-tag's own CSS uppercases it for display).
function formatRole(role) {
  return String(role || "")
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
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

// Progressive disclosure: forensic-level detail (raw objects, full ladders)
// stays closed by default, one click away -- the plain-sentence summary next
// to it is always visible. Ids only need to be unique within one rendered
// section, so a short local counter per call site is enough.
let _disclosureSeq = 0;
function disclosureHTML(label, bodyHtml, { count = null, defaultOpen = false } = {}) {
  const id = `disclosure-${++_disclosureSeq}`;
  const countHtml = count != null ? `<span class="mono-small">${esc(count)}</span>` : "";
  return `
    <div class="disclosure" data-open="${defaultOpen}">
      <button type="button" class="disclosure-toggle" data-target="${id}">
        <span class="disclosure-chevron">&#9656;</span>${esc(label)}${countHtml}
      </button>
      <div class="disclosure-body${defaultOpen ? "" : " hidden"}" id="${id}">${bodyHtml}</div>
    </div>`;
}

// number is the stage marker ("STAGE 1".."STAGE 7") -- a distinct, quieter
// mono element separate from the title, so the operator never has to wonder
// where they are: clicking AGENTS or scrolling to it always reads back as
// "STAGE 1 -- Agents & conflict", not just a generic section heading.
function blockHeader(number, title, meta) {
  return `
    <div class="block-header">
      <span class="block-number">${esc(number)}</span>
      <span class="block-title">${esc(title)}</span>
      ${meta ? `<span class="block-meta">${esc(meta)}</span>` : ""}
    </div>`;
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

// Section-scoped, never page-wide: a failed section shows its own compact
// error with a retry action, and the rest of the case stays usable. Never
// fabricates fallback data -- retrying just re-runs the same real request.
function renderErrorPanel(container, err, onRetry) {
  const status = err instanceof ApiError ? err.status : "--";
  const retryId = onRetry ? `retry-${++_disclosureSeq}` : null;
  container.innerHTML = `
    <div class="error-box">
      <div class="error-box-text">
        <strong>Couldn't load this section</strong>
        <p>${esc(errorMessage(err))} (HTTP ${esc(status)})</p>
      </div>
      ${onRetry ? `<button type="button" class="btn btn--ghost" id="${retryId}">Retry</button>` : ""}
    </div>`;
  if (onRetry) {
    document.getElementById(retryId).addEventListener("click", onRetry);
  }
}

// -- health ----------------------------------------------------------------

// Infrastructure status is deliberately invisible when everything works --
// a judge should read "Sentinel is working" from the product itself, not
// from a status pill. This banner only ever appears when there's an actual
// problem to surface, and stays subtle (a line of text, not a hero element)
// even then. The health check itself still runs and is still accurate.
async function refreshHealth() {
  const el = document.getElementById("health-banner");
  const show = (text, tone) => {
    el.className = tone === "warn" ? "health-banner health-banner--warn" : "health-banner";
    el.textContent = text;
  };
  const hide = () => el.classList.add("hidden");

  try {
    const body = await apiGet("/health");
    const dbStatus = body.application && body.database ? body.database.status : "unknown";
    if (dbStatus === "ok") {
      hide();
    } else if (dbStatus === "not_configured") {
      show("Database not configured -- persisted data is unavailable.", "warn");
    } else {
      show(`Database unavailable (${dbStatus}).`, "bad");
    }
  } catch (err) {
    show("Cannot reach the Sentinel backend.", "bad");
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

function updateCaseSelectLabel() {
  const label = document.getElementById("case-select-label");
  const current = state.cases.find((c) => c.case_id === state.selectedCaseId);
  label.textContent = current ? current.external_case_id || current.case_id : "Select a case…";
}

// Attention: derived entirely from the real `human_review_required` flag
// GET /api/cases already computes server-side (backend/api/service.py --
// true for a FAILED run, or any outcome other than PROCEED). No new rule is
// invented here; this only summarizes and categorizes what the API already
// says, the same way the case-list badges do.
function categorizeAttention(c) {
  if (c.status === "FAILED") return "FAILED";
  if (c.outcome === "ESCALATE") return "ESCALATE";
  if (c.outcome === "AMBIGUOUS") return "AMBIGUOUS";
  return "NEEDS REVIEW"; // HOLD, or any other non-PROCEED outcome
}

function renderAttentionPanel(visibleCases) {
  const container = document.getElementById("attention-panel");
  if (!container) return;

  const attention = visibleCases.filter((c) => c.human_review_required);

  if (attention.length === 0) {
    container.innerHTML = `
      <span class="attention-eyebrow">Attention</span>
      <span class="attention-summary attention-summary--clear">All cases are clear</span>`;
    return;
  }

  const counts = {};
  attention.forEach((c) => {
    const key = categorizeAttention(c);
    counts[key] = (counts[key] || 0) + 1;
  });
  const breakdown = Object.entries(counts)
    .map(([label, count]) => `<li>${count} ${esc(label)}</li>`)
    .join("");

  container.innerHTML = `
    <span class="attention-eyebrow">Attention</span>
    <span class="attention-summary attention-summary--warn">${attention.length} case${attention.length === 1 ? "" : "s"} need${attention.length === 1 ? "s" : ""} attention</span>
    <ul class="attention-breakdown">${breakdown}</ul>
    <button type="button" class="btn" id="review-attention-btn">Review cases</button>`;

  document.getElementById("review-attention-btn").addEventListener("click", () => {
    document.getElementById("case-select-btn").click();
  });
}

async function loadCases() {
  const container = document.getElementById("case-list");
  try {
    state.cases = await apiGet("/cases");
  } catch (err) {
    renderErrorPanel(container, err, loadCases);
    return;
  }
  updateCaseSelectLabel();
  // Presentation-only filter: GET /api/cases above already returned every
  // persisted case, untouched -- this only decides what the judge-facing
  // list renders.
  const visibleCases = state.cases.filter((c) => !HIDDEN_EXTERNAL_CASE_IDS.has(c.external_case_id));
  renderAttentionPanel(visibleCases);
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
    btn.addEventListener("click", () => {
      closePopovers();
      selectCase(btn.dataset.caseId, null);
    });
  });
}

// -- scenario lab (existing deterministic fallback/demo mode) ----------------

async function loadScenarios() {
  const container = document.getElementById("scenario-list");
  try {
    state.scenarios = await apiGet("/scenarios");
  } catch (err) {
    renderErrorPanel(container, err, loadScenarios);
    return;
  }
  container.innerHTML = state.scenarios
    .map(
      (s) => `
        <button class="scenario-item" data-scenario-id="${esc(s.id)}">
          <span>${esc(s.title)}</span>
          ${s.description ? `<span class="scenario-item-desc">${esc(s.description)}</span>` : ""}
        </button>`
    )
    .join("");
  container.querySelectorAll(".scenario-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      closePopovers();
      runScenario(btn.dataset.scenarioId, btn);
    });
  });
}

async function runScenario(scenarioId, btn) {
  btn.disabled = true;
  const original = btn.innerHTML;
  btn.innerHTML = "<span>Running…</span>";
  try {
    const outcome = await apiPost(`/scenarios/${encodeURIComponent(scenarioId)}/run`, {});
    await loadCases();
    selectCase(outcome.case_id, outcome.case_run_id);
  } catch (err) {
    alert(errorMessage(err));
  } finally {
    btn.disabled = false;
    btn.innerHTML = original;
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
  closePopovers();
  document.getElementById("new-case-panel").classList.remove("hidden");
  document.getElementById("empty-state").classList.add("hidden");
  document.getElementById("case-detail").classList.add("hidden");
  document.getElementById("pipeline-nav").classList.add("hidden");
}

function closeNewCasePanel() {
  document.getElementById("new-case-panel").classList.add("hidden");
  if (state.selectedCaseId) {
    document.getElementById("case-detail").classList.remove("hidden");
    document.getElementById("pipeline-nav").classList.remove("hidden");
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
  document.getElementById("pipeline-nav").classList.remove("hidden");

  document.querySelectorAll(".case-item").forEach((btn) => {
    btn.classList.toggle("case-item--active", btn.dataset.caseId === caseId);
  });
  updateCaseSelectLabel();

  await renderOverview();
  await loadAllSections();
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
    renderErrorPanel(container, err, renderOverview);
    return;
  }

  const run = detail.run;
  const govern = detail.govern_result;
  const receipt = detail.execution_receipt;

  if (!run) {
    container.className = "panel case-overview";
    container.innerHTML = `
      <dl class="kv-grid">
        <div><dt>Case</dt><dd class="mono">${esc(detail.case.id)}</dd></div>
        <div><dt>External ID</dt><dd class="mono">${esc(detail.case.external_case_id || "--")}</dd></div>
        <div><dt>Created</dt><dd class="mono">${esc(fmtTime(detail.case.created_at))}</dd></div>
      </dl>
      <p class="muted" style="margin-top:12px">This case has no runs yet.</p>`;
    return;
  }

  const outcomeText = govern ? govern.outcome : run.status === "FAILED" ? "FAILED" : "PENDING";
  const outcomeCls = outcomeTone(govern ? govern.outcome : run.status);

  // Outcome-first: the colour on the panel's top edge and the size of the
  // word are the strongest signal on the page, per the decision-summary
  // pattern -- this IS the case the operator is investigating.
  container.className = `panel case-overview case-overview--${outcomeCls}`;
  container.innerHTML = `
    <div class="decision-summary-head" style="margin-bottom:14px">
      <span class="outcome-word outcome-word--${outcomeCls}">${esc(outcomeText)}</span>
      ${receipt ? badge(receipt.status, receiptTone(receipt.status)) : ""}
    </div>
    <dl class="kv-grid">
      <div><dt>Case</dt><dd class="mono">${esc(detail.case.external_case_id || detail.case.id)}</dd></div>
      <div><dt>Run</dt><dd class="mono">${esc(run.id)}</dd></div>
      <div><dt>Status</dt><dd>${badge(run.status, outcomeTone(run.status))}</dd></div>
      <div><dt>Entity type</dt><dd>${esc(run.entity_type)}</dd></div>
      <div><dt>Run created</dt><dd class="mono">${esc(fmtTime(run.created_at))}</dd></div>
    </dl>`;
}

// -- decision record spine: all stages render at once, no tab switching -----------

function initPipelineNav() {
  document.querySelectorAll(".pipeline-link").forEach((link) => {
    link.addEventListener("click", () => {
      const target = document.getElementById(link.dataset.jump);
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

// Scroll-aware active stage: the sticky pipeline nav must always name
// whichever stage the user is currently reading, not just whichever they
// last clicked. rootMargin shrinks the observed viewport to a band just
// under the sticky nav, so a stage becomes active as soon as its heading
// crosses into view -- the same signal driving both the nav link and a
// quiet echo (`.block--active`) on the section heading itself.
function initPipelineObserver() {
  const sections = Array.from(document.querySelectorAll("#case-detail .block"));
  if (sections.length === 0) return;

  const setActive = (id) => {
    document.querySelectorAll(".pipeline-link").forEach((link) => {
      link.classList.toggle("active", link.dataset.jump === id);
    });
    sections.forEach((s) => s.classList.toggle("block--active", s.id === id));
  };

  const observer = new IntersectionObserver(
    (entries) => {
      const visible = entries.filter((e) => e.isIntersecting);
      if (visible.length === 0) return;
      visible.sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      setActive(visible[0].target.id);
    },
    { rootMargin: "-56px 0px -65% 0px", threshold: 0 }
  );

  sections.forEach((s) => observer.observe(s));
}

function loadAllSections() {
  if (!state.selectedCaseId) return Promise.resolve();
  return Promise.all([
    loadAgentsTab(),
    loadResolveTab(),
    loadWeighTab(),
    loadGovernTab(),
    loadExecutorTab(),
    loadAuditTab(),
    loadHistoryTab(),
  ]);
}

// C. Agent disagreement -----------------------------------------------------

async function loadAgentsTab() {
  const container = document.getElementById("panel-agents");
  container.innerHTML = '<p class="muted">Loading agents &amp; conflict&hellip;</p>';
  let evidence;
  try {
    evidence = await apiGet(`/cases/${encodeURIComponent(state.selectedCaseId)}/evidence${runQuery()}`);
  } catch (err) {
    renderErrorPanel(container, err, loadAgentsTab);
    return;
  }

  const agents = evidence.agents || [];
  const conflict = evidence.conflict;

  const agentCards = agents
    .map(
      (a) => `
      <div class="agent-card">
        <div class="agent-card-header">
          <span class="role-tag">${esc(formatRole(a.role))}</span>
        </div>
        <span class="agent-name">${esc(a.agent_name)}</span>
        <span class="agent-action">${esc(a.proposed_action)}</span>
        <span data-numeric class="mono-small">confidence ${fmtNum(a.confidence)}</span>
        ${disclosureHTML("Full payload", jsonBlock(a.payload))}
      </div>`
    )
    .join("");

  container.innerHTML = `
    ${blockHeader("STAGE 1", "Agents & conflict")}
    <div class="agent-grid">${agentCards || '<p class="muted">No agent outputs recorded.</p>'}</div>
    ${
      conflict
        ? `
      <div class="conflict-box conflict-box--${conflict.conflict ? "yes" : "no"}">
        <div>${badge(conflict.conflict ? "CONFLICT" : "NO CONFLICT", conflict.conflict ? "info" : "good")}</div>
        <div><span class="label">Action A</span> ${esc(conflict.action_a)} &nbsp;&middot;&nbsp; <span class="label">Action B</span> ${esc(conflict.action_b)}</div>
        <div>${esc(conflict.reason)}</div>
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
    renderErrorPanel(container, err, loadResolveTab);
    return;
  }

  const candidates = evidence.candidates || [];
  if (candidates.length === 0) {
    container.innerHTML = `${blockHeader("STAGE 2", "Resolve")}<p class="muted">RESOLVE produced no candidates for this run.</p>`;
    return;
  }

  container.innerHTML = `
    ${blockHeader("STAGE 2", "Resolve", `${candidates.length} candidate${candidates.length === 1 ? "" : "s"}`)}
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
          <div>${esc(c.rationale)}</div>
          <div class="mono-small" style="margin-top:6px">${esc(c.source_rule)}</div>
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
    renderErrorPanel(container, err, loadWeighTab);
    return;
  }

  const weigh = evidence.weigh_result;
  const candidates = (evidence.candidates || []).slice().sort((a, b) => {
    const rankA = a.score ? a.score.rank : Infinity;
    const rankB = b.score ? b.score.rank : Infinity;
    return rankA - rankB;
  });

  if (!weigh) {
    container.innerHTML = `${blockHeader("STAGE 3", "Weigh")}<p class="muted">WEIGH did not produce a result for this run.</p>`;
    return;
  }

  const scoreRows = candidates
    .map((c) => {
      const s = c.score;
      if (!s) return `<tr><td>${esc(c.candidate_id)}</td><td colspan="6" class="muted">not scored</td></tr>`;
      return `
        <tr${s.rank === 1 ? ' class="rank-first"' : ""}>
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
    ${blockHeader("STAGE 3", "Weigh", `profile ${weigh.profile_name}`)}
    <table class="score-table">
      <thead>
        <tr><th>Candidate</th><th>Rank</th><th>Total score</th><th>Eligible</th><th>Basis</th><th>Originating agent</th><th>Origin. confidence</th></tr>
      </thead>
      <tbody>${scoreRows}</tbody>
    </table>

    <div class="weigh-grid">
      <dl class="kv-grid">
        <div><dt>Profile</dt><dd>${esc(weigh.profile_name)} (${esc(weigh.profile_reason)})</dd></div>
        <div><dt>Case confidence</dt><dd class="mono">${fmtNum(weigh.case_confidence)} via ${esc(weigh.confidence_method)}</dd></div>
        <div><dt>Evidence complete</dt><dd>${badge(weigh.evidence_complete ? "yes" : "no", weigh.evidence_complete ? "good" : "warn")}</dd></div>
      </dl>
      <dl class="kv-grid">
        <div><dt>Ambiguity detected</dt><dd>${badge(weigh.ambiguity_detected ? "yes" : "no", weigh.ambiguity_detected ? "warn" : "good")}</dd></div>
        <div><dt>Near-tie group</dt><dd>${esc((weigh.near_tie_group || []).join(", ") || "--")}</dd></div>
        <div><dt>Top gap</dt><dd class="mono">${fmtNum(weigh.top_gap, 4)}</dd></div>
      </dl>
    </div>

    ${disclosureHTML("Ambiguity signals", jsonBlock(weigh.ambiguity_signals))}
    ${disclosureHTML("Weights used", jsonBlock(weigh.weights_used))}
    ${disclosureHTML(
      "Candidate objective impacts & constraint findings",
      `<div class="candidate-grid">
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
      </div>`,
      { count: candidates.length }
    )}
    ${disclosureHTML("Constraint evaluation (run-level)", jsonBlock(weigh.constraint_evaluation))}`;
}

// F. Govern -----------------------------------------------------------------

async function loadGovernTab() {
  const container = document.getElementById("panel-govern");
  container.innerHTML = '<p class="muted">Loading GOVERN decision&hellip;</p>';
  let decision;
  try {
    decision = await apiGet(`/cases/${encodeURIComponent(state.selectedCaseId)}/decision${runQuery()}`);
  } catch (err) {
    renderErrorPanel(container, err, loadGovernTab);
    return;
  }

  if (!decision.govern_result) {
    container.innerHTML = `${blockHeader("STAGE 4", "Govern")}<p class="muted">${esc(decision.note || "GOVERN has not produced a result for this run.")}</p>`;
    return;
  }

  const tone = outcomeTone(decision.outcome);
  // rationale.outcome_sentence is GOVERN's own plain-English explanation of
  // its decision (e.g. "PROCEED: candidate 'x' is permitted and its WEIGH
  // score 0.75 meets proceed_min_score 0.75."); outcome_basis is the same
  // fact as a short machine code (e.g. SCORE_AT_OR_ABOVE_PROCEED_MIN). Both
  // come straight from the API -- nothing here composes or infers either.
  const whyText = (decision.rationale && decision.rationale.outcome_sentence) || decision.outcome_basis;

  container.innerHTML = `
    ${blockHeader("STAGE 4", "Govern -- the authorization boundary")}
    <div class="decision-summary decision-summary--govern decision-summary--${tone}">
      <div class="decision-summary-head">
        <span class="outcome-word outcome-word--${tone}">${esc(decision.outcome)}</span>
        <span class="mono-small">execution ${decision.execution_authorized ? "authorized" : "not authorized"}</span>
      </div>
      <div class="decision-summary-why">${esc(whyText)}</div>
      <div class="decision-summary-foot">
        <span>basis ${esc(decision.outcome_basis)}</span>
        <span>policy ${esc(decision.policy_hash.slice(0, 12))}&hellip;</span>
        <span>decided by GOVERN</span>
        <span>profile ${esc(decision.profile_selected)}</span>
      </div>
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

    <dl class="kv-grid" style="margin-top:14px">
      <div><dt>Decision id</dt><dd class="mono">${esc(decision.decision_id)}</dd></div>
      <div><dt>Objectives considered</dt><dd>${esc((decision.objectives_considered || []).join(", "))}</dd></div>
    </dl>

    ${disclosureHTML("Authorized actions", jsonBlock(decision.authorized_actions))}
    ${disclosureHTML("Score band", jsonBlock(decision.score_band))}
    ${disclosureHTML("Permission evaluation", jsonBlock(decision.permission_evaluation))}
    ${disclosureHTML("Escalation", jsonBlock(decision.escalation))}
    ${disclosureHTML("Rationale", jsonBlock(decision.rationale))}`;
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
    renderErrorPanel(container, err, loadExecutorTab);
    return;
  }

  const receipt = detail.execution_receipt;
  if (!receipt) {
    container.innerHTML = `${blockHeader("STAGE 5", "Executor")}<p class="muted">EXECUTOR has not produced a receipt for this run (GOVERN may not have authorized execution, or the run has not reached EXECUTOR yet).</p>`;
    return;
  }

  const tone = receiptTone(receipt.status);
  // The connector reads GOVERN's own outcome back out of the receipt's
  // authorization block -- EXECUTOR's own record of what it was told, not
  // a second call to /decision -- so it's still exactly one real value,
  // never recomputed here.
  const auth = receipt.authorization || {};

  container.innerHTML = `
    ${blockHeader("STAGE 5", "Executor -- the real-world call")}
    <div class="stage-connector">
      <span>Govern: ${esc(auth.outcome || "--")} &middot; ${auth.execution_authorized ? "authorized" : "not authorized"}</span>
      <span class="arrow">&#8594;</span>
      <span>Executor</span>
    </div>
    <div class="decision-summary decision-summary--${tone}">
      <div class="decision-summary-head">
        <span class="outcome-word outcome-word--${tone}">${esc(receipt.status)}</span>
        <span class="mono-small">${esc(receipt.execution_mode)} execution</span>
      </div>
      <div class="decision-summary-foot">
        <span>receipt ${esc(receipt.receipt_id.slice(0, 12))}&hellip;</span>
      </div>
    </div>

    ${disclosureHTML("Executed actions", jsonBlock(receipt.executed_actions), { count: (receipt.executed_actions || []).length })}
    ${receipt.status === "REJECTED" ? disclosureHTML("Rejection", jsonBlock(receipt.rejection), { defaultOpen: true }) : ""}
    ${disclosureHTML("Authorization block", jsonBlock(receipt.authorization))}
    ${disclosureHTML("Authorization checks (ladder trail)", jsonBlock(receipt.authorization_checks), { count: (receipt.authorization_checks || []).length })}`;
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
    renderErrorPanel(container, err, loadAuditTab);
    return;
  }

  const events = timeline.events || [];
  const reviews = timeline.human_reviews || [];

  container.innerHTML = `
    ${blockHeader("STAGE 6", "Audit trail", `${events.length} event${events.length === 1 ? "" : "s"}`)}
    <ol class="timeline">
      ${events
        .map(
          (e) => `
        <li class="timeline-item timeline-item--${stageTone(e.outcome)}">
          <div class="timeline-stage">${esc(e.stage)} ${badge(e.outcome, stageTone(e.outcome))}</div>
          <div class="timeline-time">${esc(fmtTime(e.occurred_at))}</div>
          <div class="muted">${esc(e.summary)}</div>
          ${e.detail ? disclosureHTML("Detail", jsonBlock(e.detail)) : ""}
        </li>`
        )
        .join("") || '<li class="muted">No audit events recorded.</li>'}
    </ol>

    <h4>Human reviews</h4>
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
    renderErrorPanel(container, err, loadHistoryTab);
    return;
  }

  if (runs.length === 0) {
    container.innerHTML = `${blockHeader("STAGE 7", "Run history")}<p class="muted">No runs recorded for this case.</p>`;
    return;
  }

  container.innerHTML = `
    ${blockHeader("STAGE 7", "Run history", `${runs.length} run${runs.length === 1 ? "" : "s"}`)}
    <div class="run-list">
      ${runs
        .map((r) => {
          const active = r.case_run_id === state.selectedRunId || (!state.selectedRunId && r === runs[0]);
          return `
          <button class="run-item${active ? " run-item--active" : ""}" data-run-id="${esc(r.case_run_id)}">
            <span class="mono-small">${esc(fmtTime(r.created_at))}</span>
            ${badge(r.status, outcomeTone(r.status))}
            ${r.outcome ? badge(r.outcome, outcomeTone(r.outcome)) : ""}
            ${badge(r.executed ? "EXECUTED" : "NOT EXECUTED", r.executed ? "good" : "neutral")}
            <span class="mono-small">${esc(r.case_run_id)}</span>
          </button>`;
        })
        .join("")}
    </div>`;

  container.querySelectorAll(".run-item").forEach((btn) => {
    btn.addEventListener("click", async () => {
      state.selectedRunId = btn.dataset.runId;
      await renderOverview();
      await loadAllSections();
    });
  });
}

// -- wire-up ---------------------------------------------------------------------

function initDisclosures() {
  // Delegated: disclosure buttons are re-created every time a section
  // re-renders, so one listener on the document handles all of them.
  document.addEventListener("click", (event) => {
    const toggle = event.target.closest(".disclosure-toggle");
    if (!toggle) return;
    const body = document.getElementById(toggle.dataset.target);
    if (!body) return;
    const open = body.classList.toggle("hidden") === false;
    toggle.closest(".disclosure").dataset.open = String(open);
  });
}

// -- top-of-page popovers: case selector + scenario lab -------------------------
// Replaces the old permanent sidebar -- case/scenario navigation now lives in
// two compact popovers anchored to the control bar, closed by default.

function closePopovers() {
  document.querySelectorAll(".popover").forEach((p) => p.classList.add("hidden"));
  document.querySelectorAll("[aria-expanded]").forEach((b) => b.setAttribute("aria-expanded", "false"));
}

function togglePopover(buttonId, popoverId) {
  const btn = document.getElementById(buttonId);
  const pop = document.getElementById(popoverId);
  btn.addEventListener("click", (event) => {
    event.stopPropagation();
    const willOpen = pop.classList.contains("hidden");
    closePopovers();
    if (willOpen) {
      pop.classList.remove("hidden");
      btn.setAttribute("aria-expanded", "true");
    }
  });
  pop.addEventListener("click", (event) => event.stopPropagation());
}

function initPopovers() {
  togglePopover("case-select-btn", "case-popover");
  togglePopover("scenario-select-btn", "scenario-popover");
  document.addEventListener("click", closePopovers);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closePopovers();
  });
}

function init() {
  refreshHealth();
  loadCases();
  loadScenarios();
  initPipelineNav();
  initPipelineObserver();
  initDisclosures();
  initPopovers();

  document.getElementById("refresh-cases").addEventListener("click", loadCases);
  document.getElementById("refresh-current-case").addEventListener("click", () => {
    if (!state.selectedCaseId) return;
    renderOverview();
    loadAllSections();
  });
  document.getElementById("open-new-case").addEventListener("click", () => {
    openNewCasePanel();
    buildAgentFieldset("agent_a");
    buildAgentFieldset("agent_b");
  });
  document.getElementById("close-new-case").addEventListener("click", closeNewCasePanel);
  document.getElementById("new-case-form").addEventListener("submit", submitNewCase);
}

document.addEventListener("DOMContentLoaded", init);
