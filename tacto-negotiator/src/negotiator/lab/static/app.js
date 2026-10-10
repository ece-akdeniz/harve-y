"use strict";

const $ = (id) => document.getElementById(id);
const state = { runs: [], loggedIn: false, memoryGeneration: 0, refreshPromise: null, detail: null, detailRequest: 0, comparison: null, table: { page: 1, pageSize: 25, sortKey: "updated_at", direction: "desc" } };
const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 });
const euro = new Intl.NumberFormat(undefined, { style: "currency", currency: "EUR", maximumFractionDigits: 2 });
const score = (value) => typeof value === "number" && Number.isFinite(value) ? number.format(value * 100) : "—";
const signed = (value) => typeof value === "number" && Number.isFinite(value)
  ? `${value > 0 ? "+" : ""}${number.format(value * 100)}` : "—";
const deltaClass = (value) => value == null ? "neutral" : value > 0 ? "positive" : value < 0 ? "negative" : "neutral";
const label = (value) => String(value ?? "Unknown").replaceAll("_", " ");

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = String(text);
  if (className) node.className = className;
  return node;
}

function badge(text, kind = text) {
  const known = new Set(["running", "completed", "failed", "interrupted", "imported"]);
  return element("span", label(text), `badge ${known.has(kind) ? kind : ""}`);
}

function dateText(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unknown" : date.toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function relative(value) {
  const minutes = Math.max(0, (Date.now() - new Date(value).getTime()) / 60000);
  if (!Number.isFinite(minutes)) return "—";
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${Math.floor(minutes)}m ago`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h ago`;
  return dateText(value);
}

async function api(path, options = {}) {
  let response;
  try { response = await fetch(path, {
    credentials: "same-origin", cache: "no-store", ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
    signal: AbortSignal.timeout(8000),
  }); } catch (error) {
    if (error.name === "TimeoutError" || error.name === "AbortError") {
      throw new Error("The dashboard connection timed out. Check that the host laptop and VS Code tunnel are running, then try again.");
    }
    throw new Error(`Could not connect to the dashboard. ${error.message}`);
  }
  const body = await response.json().catch(() => {
    throw new Error("The tunnel returned an unexpected response. Open the public HTTPS address directly and complete any tunnel access prompt, then reload.");
  });
  if (!response.ok) {
    if (response.status === 401 && path !== "/api/login") showLogin();
    const error = new Error(body.error || `Request failed (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return body;
}

function showLogin() {
  state.memoryGeneration++;
  globalThis.MemoryDashboard?.reset();
  globalThis.LoopDashboard?.reset();
  globalThis.ScoreHistory?.reset();
  state.table.page = 1;
  state.loggedIn = false;
  state.runs = [];
  state.detail = null;
  state.comparison = null;
  if ($("detail-dialog").open) $("detail-dialog").close();
  $("detail-content").replaceChildren();
  $("runs-body").replaceChildren();
  $("workspace").hidden = true;
  $("login-view").hidden = false;
}

function showWorkspace() {
  state.loggedIn = true;
  $("login-view").hidden = true;
  $("workspace").hidden = false;
  $("password").value = "";
  $("login-error").textContent = "";
}

function switchView(view) {
  for (const name of ["runs", "compare", "history", "memory"]) {
    $(name + "-view").hidden = name !== view;
    $("nav-" + name).classList.toggle("active", name === view);
    $("nav-" + name).setAttribute("aria-current", name === view ? "page" : "false");
  }
  $("loop-view").hidden = view !== "runs";
  const titles = {runs: ["Experiments", "Experiment lab", "Small changes. Clear comparisons. Better negotiations."],
    compare: ["Compare runs", "Find the difference", "Understand where a change helped, and where it didn't."],
    history: ["Score history", "Progress over time", "Follow each supplier and case, from the first attempt to the latest."],
    memory: ["Memory", "Evidence into memory", "Inspect supplier history, candidate lessons and frozen discovery cohorts."]};
  const [crumb, title, description] = titles[view];
  $("breadcrumb").textContent = crumb;
  $("page-title").replaceChildren(document.createTextNode(title), element("span", ".", "title-dot"));
  $("page-description").textContent = description;
  if (view === "history") globalThis.ScoreHistory?.refresh();
  if (view === "memory") globalThis.MemoryDashboard?.refresh();
}

function updateOptions(id, entries, placeholder) {
  const select = $(id);
  const signature = JSON.stringify(entries);
  if (select.dataset.options === signature) return;
  select.dataset.options = signature;
  const previous = select.value;
  select.replaceChildren(new Option(placeholder, ""));
  for (const [value, text] of entries) select.add(new Option(text, value));
  if (entries.some(([value]) => value === previous)) select.value = previous;
}

function renderSummary(payload) {
  $("team-name").textContent = payload.team || "y/agent";
  $("stat-total").textContent = state.runs.length;
  $("stat-running").textContent = state.runs.filter((r) => r.status === "running").length;
  $("stat-failed").textContent = state.runs.filter((r) => ["failed", "interrupted"].includes(r.status)).length;
  const quota = payload.quota;
  $("stat-quota").textContent = quota?.left ?? "—";
  $("quota-caption").textContent = quota
    ? `${quota.used ?? "?"} / ${quota.limit ?? "?"} used · ${quota.checked_at ? relative(quota.checked_at) : "last snapshot"}`
    : "No quota snapshot yet";
  $("quota-caption").title = quota?.checked_at ? `Snapshot: ${dateText(quota.checked_at)}. All laptops share this quota.` : "Import history or run a hosted experiment to record quota.";
  const authors = [...new Set(state.runs.map((r) => r.author || "Unknown"))].sort();
  updateOptions("filter-author", authors.map((a) => [a, a]), "All teammates");
  const options = state.runs.map((r) => [r.run_id, `${r.name} · ${r.author} · ${r.environment}`]);
  updateOptions("baseline-select", options, "Choose a baseline…");
  updateOptions("candidate-select", options, "Choose a candidate…");
}

const runColumns = ["name", "author", "environment", "score", "attempts", "status", "updated_at"];
function experimentPage(rows, options = {}) {
  const {query = "", author = "", environment = "", status = "", sortKey = "updated_at", direction = "desc"} = options;
  const search = query.trim().toLowerCase();
  const runs = rows.filter(r =>
    (!search || [r.name, r.hypothesis, r.agent, r.author, r.run_id].join(" ").toLowerCase().includes(search)) &&
    (!author || (r.author || "Unknown") === author) && (!environment || r.environment === environment) &&
    (!status || r.status === status));
  const collator = new Intl.Collator(undefined, {numeric: true, sensitivity: "base"});
  const value = r => {
    if (sortKey === "score") return r.metrics?.mean_score ?? r.metrics?.observed_mean ?? null;
    if (sortKey === "attempts") return r.metrics?.completed ?? null;
    if (sortKey === "updated_at") { const time = Date.parse(r.updated_at); return Number.isFinite(time) ? time : null; }
    return r[sortKey] ?? null;
  };
  runs.sort((a, b) => {
    const x = value(a), y = value(b);
    if (x == null && y != null) return 1;
    if (y == null && x != null) return -1;
    const cmp = x == null ? 0 : typeof x === "number" && typeof y === "number" ? x - y : collator.compare(String(x), String(y));
    return cmp * (direction === "asc" ? 1 : -1) || collator.compare(a.run_id, b.run_id);
  });
  const pageSize = Math.max(1, Math.floor(Number(options.pageSize) || 25));
  const pages = Math.max(1, Math.ceil(runs.length / pageSize));
  const page = Math.max(1, Math.min(pages, Math.floor(Number(options.page) || 1)));
  return {rows: runs.slice((page - 1) * pageSize, page * pageSize), total: runs.length, page, pages, pageSize};
}

function renderRuns() {
  const result = experimentPage(state.runs, {...state.table, query: $("search").value,
    author: $("filter-author").value, environment: $("filter-environment").value, status: $("filter-status").value});
  state.table.page = result.page;
  const runs = result.rows;
  $("page-range").textContent = result.total ? `${(result.page - 1) * result.pageSize + 1}–${Math.min(result.page * result.pageSize, result.total)} of ${result.total} experiments` : "0 experiments";
  $("page-position").textContent = `Page ${result.page} of ${result.pages}`;
  $("page-prev").disabled = result.page === 1;
  $("page-next").disabled = result.page === result.pages;
  for (const key of runColumns) {
    const active = state.table.sortKey === key;
    $("sort-" + key).parentElement.setAttribute("aria-sort", active ? (state.table.direction === "asc" ? "ascending" : "descending") : "none");
    $("sort-" + key).querySelector(".sort-indicator").textContent = active ? (state.table.direction === "asc" ? "↑" : "↓") : "↕";
  }
  $("run-count").textContent = result.total;
  $("runs-body").replaceChildren();
  $("empty-state").hidden = state.runs.length > 0;
  $("no-matches").hidden = state.runs.length === 0 || runs.length > 0;
  for (const run of runs) {
    const row = element("tr");
    const nameCell = element("td");
    const name = element("button", run.name, "run-name");
    name.title = run.hypothesis || run.name;
    name.addEventListener("click", () => openDetail(run.run_id));
    nameCell.append(name, element("span", `${run.agent || "Unknown agent"} · ${run.source === "imported" ? "Imported history" : run.provenance?.dirty ? "Uncommitted changes" : run.provenance?.commit?.slice(0, 7) || "Unknown revision"}`, "run-meta"));
    const ownerCell = element("td");
    const owner = element("span", null, "owner");
    owner.append(element("span", (run.author || "?").slice(0, 2).toUpperCase(), "owner-initial"), document.createTextNode(run.author || "Unknown"));
    ownerCell.append(owner);
    const env = element("td"); env.append(badge(run.environment));
    const metrics = run.metrics || {};
    const partial = metrics.mean_score == null && metrics.observed_mean != null;
    const scoreCell = element("td");
    scoreCell.append(element("span", score(metrics.mean_score ?? metrics.observed_mean), `score${partial ? " partial" : ""}`), element("span", partial ? `Partial · ${metrics.scored}/${metrics.planned} scored` : metrics.mean_score == null ? "Awaiting outcome" : "out of 100", "subline"));
    if (metrics.recovered) scoreCell.append(element("span", `${metrics.recovered} recovered outcome${metrics.recovered === 1 ? "" : "s"}`, "subline"));
    const attempts = element("td", `${metrics.completed ?? 0} / ${metrics.planned ?? "?"}`);
    if (metrics.failed) attempts.append(element("span", `${metrics.failed} failed`, "subline negative"));
    const status = element("td"); status.append(badge(run.status));
    const updated = element("td", relative(run.updated_at)); updated.title = dateText(run.updated_at);
    row.append(nameCell, ownerCell, env, scoreCell, attempts, status, updated);
    $("runs-body").append(row);
  }
}

async function refresh({ afterLogin = false } = {}) {
  while (state.refreshPromise) {
    if (!afterLogin) return state.refreshPromise;
    await state.refreshPromise.catch(() => {});
  }
  const pending = refreshWorkspace({ afterLogin });
  state.refreshPromise = pending;
  try { return await pending; }
  finally { if (state.refreshPromise === pending) state.refreshPromise = null; }
}

async function refreshWorkspace({ afterLogin }) {
  try {
    const payload = await api("/api/runs");
    showWorkspace();
    const changed = JSON.stringify(payload.runs) !== JSON.stringify(state.runs);
    state.runs = payload.runs || [];
    renderSummary(payload);
    if (changed || !$("runs-body").children.length) renderRuns();
    $("global-error").hidden = true;
    $("connection").classList.remove("offline");
    $("connection-text").textContent = "Live updates";
    if (state.detail && $("detail-dialog").open) {
      const summary = state.runs.find((r) => r.run_id === state.detail.run_id);
      if (summary && (changed || summary.revision !== state.detail.revision)) await openDetail(summary.run_id, { background: true });
    }
    if (changed && state.comparison && !$("compare-view").hidden) await compare();
    await globalThis.LoopDashboard?.refresh();
    await globalThis.ScoreHistory?.refresh();
    if (!$("memory-view").hidden) await globalThis.MemoryDashboard?.refresh();
  } catch (error) {
    if (afterLogin) {
      if (error.status === 401) throw new Error("The password was accepted, but the session cookie was not received. Open the public HTTPS link directly and allow cookies for this site, then sign in again.");
      throw error;
    }
    if (state.loggedIn) {
      $("global-error").textContent = `Could not refresh. Showing the last received results. ${error.message}`;
      $("global-error").hidden = false;
      $("connection").classList.add("offline");
      $("connection-text").textContent = "Connection interrupted";
    } else if (error.status !== 401) {
      $("login-error").textContent = error.message;
    }
  }
}

function keyValues(values) {
  const list = element("dl", null, "kv");
  for (const [key, value] of values) list.append(element("dt", key), element("dd", value ?? "Unknown"));
  return list;
}

function replayLink(attempt, run) {
  if (!attempt.replay_url) return null;
  try {
    const base = new URL(run.arena_url);
    const url = new URL(attempt.replay_url, base);
    if (url.origin !== base.origin || !["http:", "https:"].includes(url.protocol) ||
        url.username || url.password || !url.pathname.startsWith("/replay/") || url.search || url.hash) return null;
    const link = element("a", `Open Tacto replay ↗`);
    link.href = url.href; link.target = "_blank"; link.rel = "noopener noreferrer";
    return link;
  } catch { return null; }
}

const reportView = { runId: null, open: new Map() };
const isNumber = value => typeof value === "number" && Number.isFinite(value);
const fieldNames = {
  unit_price: "Unit price", payment_days: "Payment terms", lead_time_days: "Lead time",
  contract_months: "Contract length", volume_per_year: "Annual volume", effective_date: "Effective date",
  ppm_commitment: "Quality commitment", tooling_eur: "Tooling", incoterm: "Incoterm",
  chargeback_eur_per_complaint: "Chargeback per complaint", index_clause: "Index clause",
  anchor: "Opening anchor", rounds: "Concession steps", close_gap: "Closing tolerance",
  final_hold_s: "Final-offer wait", p_walk: "Assumed walk-away probability", claims: "Verified claims",
  meso: "Multiple equivalent offers", estimates: "Supplier estimates", _lab_environment: "Model environment",
};
const fieldLabel = key => Object.hasOwn(fieldNames, key) ? fieldNames[key] : label(key).replace(/^./, c => c.toUpperCase());

function formatField(key, value) {
  if (value == null) return "Not recorded";
  if (typeof value === "boolean") return value ? "Enabled" : "Disabled";
  if (isNumber(value)) {
    if (["anchor", "close_gap", "p_walk"].includes(key)) return `${number.format(value * 100)}%`;
    if (key === "unit_price") return `${euro.format(value)} / unit`;
    if (key.includes("eur")) return euro.format(value);
    if (key.endsWith("_days")) return `${number.format(value)} days`;
    if (key.endsWith("_months")) return `${number.format(value)} months`;
    if (key.endsWith("_s")) return `${number.format(value)} s`;
    if (key === "ppm_commitment") return `${number.format(value)} ppm`;
    if (key === "volume_per_year") return `${number.format(value)} / year`;
    return number.format(value);
  }
  return String(value);
}

function fieldRows(value, prefix = "", depth = 0) {
  if (!value || typeof value !== "object") return [];
  return Object.entries(value).flatMap(([key, item]) => {
    const title = prefix ? `${prefix} · ${fieldLabel(key)}` : fieldLabel(key);
    if (item && typeof item === "object") {
      if (!Object.keys(item).length) return [[title, key === "estimates" ? "None supplied" : "None"]];
      if (depth >= 4) return [[title, "See technical details"]];
      return fieldRows(item, title, depth + 1);
    }
    return [[title, formatField(key, item)]];
  });
}

function reportMetrics(attempts) {
  const scored = attempts.filter(a => a.status === "completed" && isNumber(a.score));
  return {
    mean: scored.length ? scored.reduce((sum, a) => sum + a.score, 0) / scored.length : null,
    partial: scored.length !== attempts.length || !attempts.length,
    completed: attempts.filter(a => a.status === "completed").length,
    deals: attempts.filter(a => a.result?.deal === true).length,
    timeouts: attempts.length && attempts.every(a => isNumber(a.timeouts)) ? attempts.reduce((sum, a) => sum + a.timeouts, 0) : null,
    duration: attempts.some(a => isNumber(a.elapsed_s)) ? attempts.reduce((sum, a) => sum + (a.elapsed_s || 0), 0) : null,
  };
}

function threadMessages(thread) {
  const messages = Array.isArray(thread) ? thread : thread?.messages;
  return Array.isArray(messages) ? messages.filter(m => m && typeof m === "object" && !Array.isArray(m)) : [];
}

function actionLabel(action) {
  const type = typeof action === "string" ? action : action?.type;
  return typeof type === "string" ? fieldLabel(type) : "Recorded action";
}

function disclosure(key, title, className = "report-disclosure", initiallyOpen = false) {
  const node = element("details", null, className);
  node.dataset.reportKey = key;
  node.open = reportView.open.has(key) ? reportView.open.get(key) : initiallyOpen;
  const summary = element("summary", title);
  summary.dataset.focusKey = key;
  node.append(summary);
  return node;
}

function reportStat(title, value, caption) {
  const card = element("article", null, "report-stat");
  card.append(element("span", title, "stat-label"), element("strong", value), element("span", caption, "muted"));
  return card;
}

function renderCosts(result, key) {
  const section = element("section", null, "report-panel");
  section.append(element("h4", "What the deal costs"));
  const totals = element("div", null, "cost-totals");
  totals.append(element("span", "Outcome cost"), element("strong", isNumber(result.c_deal) ? euro.format(result.c_deal) : "Not recorded"));
  section.append(totals);
  const components = Object.entries(result.cost_breakdown || {}).filter(([, value]) => isNumber(value));
  const nonzero = components.filter(([, value]) => value !== 0).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const scale = Math.max(1, ...nonzero.map(([, value]) => Math.abs(value)));
  for (const [name, value] of nonzero) {
    const row = element("div", null, "cost-component");
    const heading = element("div"); heading.append(element("span", fieldLabel(name)), element("strong", euro.format(value)));
    const bar = element("meter"); bar.min = 0; bar.max = scale; bar.value = Math.abs(value);
    bar.setAttribute("aria-label", `${fieldLabel(name)}: ${euro.format(value)}`);
    row.append(heading, bar); section.append(row);
  }
  if (!components.length) section.append(element("p", "Cost components were not recorded.", "muted"));
  const zero = components.filter(([, value]) => value === 0);
  if (zero.length) {
    const details = disclosure(`${key}:zero-cost`, `${zero.length} components with no cost`);
    details.append(keyValues(zero.map(([name]) => [fieldLabel(name), euro.format(0)]))); section.append(details);
  }
  if (isNumber(result.c_best)) section.append(keyValues([
    ["Best achievable cost", euro.format(result.c_best)],
    ["Gap to best", isNumber(result.c_deal) ? euro.format(result.c_deal - result.c_best) : "Not recorded"],
  ]));
  return section;
}

function renderConversation(threads, key, winner) {
  const section = element("section", null, "conversation-section");
  section.append(element("h4", "Negotiation history"), element("p", "Read each supplier thread in its recorded order. Expand offers to inspect the terms.", "muted"));
  const entries = Object.entries(threads || {}).filter(([, thread]) => thread && typeof thread === "object");
  if (!entries.length || threads?.evidence_truncated) {
    section.append(element("p", threads?.evidence_truncated ? "The recorded conversation exceeded the size limit. Use the Tacto replay for the full history." : "No conversation was recorded for this attempt.", "notice"));
    return section;
  }
  for (const [sid, thread] of entries) {
    const messages = threadMessages(thread);
    const name = messages.find(m => m.from !== "buyer" && m.from_name)?.from_name || sid;
    const supplier = disclosure(`${key}:supplier:${sid}`, null, "supplier-thread report-disclosure");
    supplier.firstChild.append(element("strong", name), element("span", `${messages.length} messages`, "muted"));
    if (winner === sid) supplier.firstChild.append(badge("Selected supplier", "completed"));
    const timeline = element("div", null, "message-timeline");
    if (!messages.length) timeline.append(element("p", "Messages are unavailable in this snapshot.", "notice"));
    messages.forEach((message, index) => {
      const buyer = message.from === "buyer";
      const item = element("article", null, `message-card ${buyer ? "message-buyer" : "message-supplier"}`);
      const header = element("div", null, "message-heading");
      header.append(element("strong", buyer ? "Our agent" : message.from_name || "Supplier"), element("span", `Message ${index + 1}`, "muted"));
      if (message.action) header.append(badge(actionLabel(message.action), ""));
      item.append(header);
      if (message.action?.term_sheet_id) item.append(element("p", `Offer reference: ${message.action.term_sheet_id}`, "evidence-id"));
      if (message.subject) item.append(element("p", message.subject, "message-subject"));
      if (message.body) item.append(element("p", message.body, "message-body"));
      const sheets = Array.isArray(message.term_sheets) ? message.term_sheets : [];
      sheets.forEach((sheet, sheetIndex) => {
        if (!sheet || typeof sheet !== "object") return;
        const price = sheet.terms?.unit_price;
        const offer = disclosure(`${key}:${sid}:message:${index}:offer:${sheetIndex}`,
          `Offer ${sheetIndex + 1}${isNumber(price) ? ` · ${formatField("unit_price", price)}` : ""}`, "offer-sheet report-disclosure");
        offer.append(keyValues(fieldRows(sheet.terms || {})));
        if (sheet.term_sheet_id) offer.append(element("p", sheet.term_sheet_id, "evidence-id"));
        item.append(offer);
      });
      const attachments = Array.isArray(message.attachments) ? message.attachments : [];
      if (attachments.length) item.append(element("p", `Attachments: ${attachments.map(a => a?.name || "Unnamed attachment").join(" · ")}`, "attachment-note"));
      if (Array.isArray(message.refs) && message.refs.length) item.append(element("p", `References: ${message.refs.map(r => typeof r === "string" ? r : r?.id || "Recorded reference").join(" · ")}`, "attachment-note"));
      if (Array.isArray(message.missing_fields) && message.missing_fields.length) item.append(element("p", `Missing terms: ${message.missing_fields.map(fieldLabel).join(", ")}`, "attachment-note"));
      timeline.append(item);
    });
    supplier.append(timeline); section.append(supplier);
  }
  return section;
}

function renderOutcome(result, key, recovered = false) {
  const section = element("div", null, "outcome-section");
  const grid = element("div", null, "outcome-grid");
  const agreement = element("section", null, "report-panel");
  agreement.append(element("h4", recovered ? "Recovered agreement" : "Final agreement"));
  const flags = element("div", null, "outcome-flags");
  flags.append(badge(result.deal === true ? "Deal reached" : result.deal === false ? "No deal" : "Outcome not recorded", result.deal === true ? "completed" : ""));
  flags.append(badge(result.must_haves_ok === true ? "Must-haves satisfied" : result.must_haves_ok === false ? "Must-haves broken" : "Must-haves unknown", result.must_haves_ok === false ? "failed" : ""));
  agreement.append(flags);
  if (result.terms && Object.keys(result.terms).length) agreement.append(keyValues(fieldRows(result.terms)));
  else agreement.append(element("p", "No final terms were recorded.", "muted"));
  grid.append(agreement, renderCosts(result, key)); section.append(grid);
  return section;
}

function renderDetail(run) {
  const dialog = $("detail-dialog"), content = $("detail-content");
  const sameRun = reportView.runId === run.run_id;
  const scroll = sameRun ? dialog.scrollTop : 0;
  const focused = sameRun ? document.activeElement?.dataset?.focusKey : null;
  if (sameRun) {
    for (const node of content.querySelectorAll("details[data-report-key]")) reportView.open.set(node.dataset.reportKey, node.open);
  } else { reportView.runId = run.run_id; reportView.open.clear(); }
  $("detail-title").textContent = run.name;
  $("detail-kicker").textContent = run.source === "imported" ? "IMPORTED ARENA HISTORY" : "EXPERIMENT REPORT";
  content.replaceChildren();
  content.append(element("p", run.hypothesis || "No hypothesis recorded for this experiment.", "detail-hypothesis"));
  const meta = element("div", null, "detail-meta");
  meta.append(badge(run.status), badge(run.environment), badge(run.author || "Unknown owner", ""), element("span", dateText(run.started_at), "muted"));
  content.append(meta);
  const attempts = run.attempts || [], metrics = reportMetrics(attempts);
  const stats = element("div", null, "report-stats");
  stats.append(
    reportStat(metrics.partial ? "Partial mean score" : "Mean score", score(metrics.mean), "out of 100 · recorded outcomes"),
    reportStat("Completed", `${metrics.completed} / ${attempts.length}`, `${metrics.deals} deals reached`),
    reportStat("Timeouts", metrics.timeouts == null ? "—" : number.format(metrics.timeouts), metrics.timeouts == null ? "Some evidence is unavailable" : "Across all case attempts"),
    reportStat("Negotiation time", metrics.duration == null ? "—" : `${number.format(metrics.duration)} s`, "Sum of recorded attempt durations"),
  );
  content.append(stats);
  const actions = element("div", null, "inline-actions");
  for (const [role, text] of [["baseline", "Use as baseline"], ["candidate", "Use as candidate"]]) {
    const button = element("button", text, "button secondary compact-button"); button.dataset.focusKey = role;
    button.addEventListener("click", () => {
      dialog.close(); switchView("compare"); $(`${role}-select`).value = run.run_id;
      if (role === "candidate" && run.baseline_id && state.runs.some(r => r.run_id === run.baseline_id)) $("baseline-select").value = run.baseline_id;
    }); actions.append(button);
  }
  content.append(actions);
  if (run.source === "imported") content.append(element("p", "Imported history: the original author, agent settings and code version are unknown.", "notice"));
  if (run.provenance?.dirty) content.append(element("p", "Includes uncommitted changes. Reproduction needs the saved local patch as well as the commit.", "notice"));
  content.append(element("h3", "Case results", "detail-section-title"), element("p", `${(run.cases || []).length} cases · ${run.repetitions} repeat${run.repetitions === 1 ? "" : "s"} per case. Expand a case to inspect its agreement and negotiation.`, "detail-summary"));
  attempts.forEach((attempt, index) => {
    const key = `case:${attempt.attempt_id || index}`;
    const card = disclosure(key, null, "attempt", index === 0);
    card.firstChild.append(element("strong", attempt.case_id), element("span", `Repeat ${attempt.repeat}`, "muted"), badge(attempt.status), element("span", `${score(attempt.score)} / 100`, "score"));
    const body = element("div", null, "attempt-body");
    const details = element("div", null, "case-facts");
    details.append(element("span", `${attempt.rounds ?? "—"} rounds`), element("span", isNumber(attempt.elapsed_s) ? `${number.format(attempt.elapsed_s)} s` : "Duration unknown"), element("span", `${attempt.timeouts ?? "Unknown"} timeouts`));
    const link = replayLink(attempt, run); if (link) details.append(link);
    body.append(details);
    if (attempt.error) body.append(element("p", typeof attempt.error === "string" ? attempt.error : "An execution error was recorded. See technical details.", "notice error-notice"));
    const result = attempt.result || {};
    body.append(renderOutcome(result, key));
    if (result.reconciled_result) {
      const recovered = disclosure(`${key}:recovered`, `Recovered arena outcome · ${score(result.reconciled_result.score)} / 100`, "recovered-outcome report-disclosure");
      recovered.append(element("p", "The original local status and comparison score are unchanged. This recovered evidence does not erase an execution failure.", "notice"), renderOutcome(result.reconciled_result, `${key}:recovered`, true));
      body.append(recovered);
    }
    body.append(renderConversation(attempt.threads, key, result.supplier_id));
    const technical = disclosure(`${key}:raw`, "Technical details · session and raw evidence", "raw-details report-disclosure");
    technical.append(keyValues([["Session", attempt.session_id || "Not recorded"]]), element("pre", JSON.stringify({ result, threads: attempt.threads || {} }, null, 2)));
    body.append(technical); card.append(body); content.append(card);
  });
  const setup = disclosure("setup", "Experiment setup", "setup-panel report-disclosure");
  setup.append(keyValues([["Agent", run.agent || "Unknown"], ["Environment", run.environment], ["Code version", run.provenance?.commit?.slice(0, 12) || "Unknown"]]));
  if (run.source === "imported") setup.append(element("p", "Agent settings were not recorded for imported history.", "muted"));
  else setup.append(keyValues(fieldRows(run.config || {})));
  const technical = disclosure("provenance", "Technical details · fingerprints and raw configuration", "raw-details report-disclosure");
  technical.append(keyValues([["Run ID", run.run_id], ["Code commit", run.provenance?.commit], ["Data fingerprint", run.provenance?.data_sha256], ["Dependency lock", run.provenance?.lock_sha256], ["Patch fingerprint", run.provenance?.patch_sha256], ["Arena", run.arena_url]]), element("pre", JSON.stringify(run.config || {}, null, 2)));
  setup.append(technical); content.append(setup);
  if (run.feedback?.findings?.length) {
    const feedback = disclosure("feedback", "Decision feedback · keep, change, test", "report-disclosure");
    feedback.append(element("p", run.feedback.limitation, "muted"));
    for (const finding of run.feedback.findings) {
      const item = element("article", null, "report-panel");
      item.append(element("strong", fieldLabel(finding.category)), element("p", finding.observation));
      item.append(element("p", finding.next_test));
      const refs = finding.evidence.map(ref => `${ref.attempt_id}${ref.supplier ? ` / ${ref.supplier} / message ${ref.message_index + 1}` : ""}`);
      item.append(element("p", refs.join("; "), "evidence-id"));
      feedback.append(item);
    }
    content.append(feedback);
  }
  if (focused) {
    const target = [...content.querySelectorAll("[data-focus-key]")].find(node => node.dataset.focusKey === focused);
    target?.focus({ preventScroll: true });
  }
  dialog.scrollTop = scroll;
}

async function openDetail(id, { background = false } = {}) {
  const request = ++state.detailRequest;
  try {
    const run = await api(`/api/runs/${encodeURIComponent(id)}`);
    run.feedback = await api(`/api/feedback/${encodeURIComponent(id)}`).catch(() => null);
    if (!state.loggedIn || request !== state.detailRequest) return;
    if (background && (!$("detail-dialog").open || state.detail?.run_id !== id)) return;
    if (JSON.stringify(state.detail) !== JSON.stringify(run)) renderDetail(run);
    state.detail = run;
    if (!$("detail-dialog").open) $("detail-dialog").showModal();
  } catch (error) {
    if (request !== state.detailRequest || (background && !$("detail-dialog").open)) return;
    $("global-error").textContent = `Could not open experiment. ${error.message}`; $("global-error").hidden = false;
  }
}

async function compare() {
  const baseline = $("baseline-select").value, candidate = $("candidate-select").value;
  $("comparison").hidden = true;
  $("comparison-empty").hidden = false;
  if (!baseline || !candidate) return;
  if (baseline === candidate) {
    $("global-error").textContent = "Choose two different experiments to compare."; $("global-error").hidden = false; return;
  }
  $("compare-button").disabled = true;
  try {
    const data = await api(`/api/compare?${new URLSearchParams({ baseline, candidate })}`);
    if (!state.loggedIn || $("baseline-select").value !== baseline || $("candidate-select").value !== candidate) return;
    state.comparison = { baseline, candidate };
    $("global-error").hidden = true;
    $("comparison-empty").hidden = true; $("comparison").hidden = false;
    $("compare-warnings").replaceChildren(...(data.warnings || []).map((warning) => element("div", warning, "notice")));
    $("compare-delta").textContent = signed(data.mean_delta);
    $("compare-delta").className = deltaClass(data.mean_delta);
    $("compare-caption").textContent = data.comparable
      ? `${data.baseline.name} → ${data.candidate.name}. Only cases with complete scored outcomes on both sides contribute to this summary.`
      : "An aggregate comparison is unavailable. Check the warnings for incomplete outcomes or differences in the arena and environment.";
    $("compare-body").replaceChildren();
    for (const row of data.cases || []) {
      const tr = element("tr");
      tr.append(element("td", row.case_id), element("td", score(row.baseline_mean)), element("td", score(row.candidate_mean)), element("td", signed(row.delta), deltaClass(row.delta)), element("td", `${row.baseline_scored}/${row.baseline_planned} → ${row.candidate_scored}/${row.candidate_planned}`), element("td", `${row.baseline_failed} → ${row.candidate_failed}`));
      $("compare-body").append(tr);
    }
  } catch (error) { $("global-error").textContent = `Comparison unavailable. ${error.message}`; $("global-error").hidden = false; }
  finally { $("compare-button").disabled = false; }
}

$("login-form").addEventListener("submit", async (event) => {
  event.preventDefault(); $("login-submit").disabled = true; $("login-error").textContent = "";
  try { await api("/api/login", { method: "POST", body: JSON.stringify({ password: $("password").value }) }); await refresh({ afterLogin: true }); }
  catch (error) { $("login-error").textContent = error.message; }
  finally { $("login-submit").disabled = false; }
});
async function logout() {
  try { await api("/api/logout", { method: "POST", body: "{}" }); showLogin(); }
  catch (error) { $("global-error").textContent = `Sign out failed. ${error.message}`; $("global-error").hidden = false; }
}
$("logout").addEventListener("click", logout);
$("logout-mobile").addEventListener("click", logout);
$("nav-runs").addEventListener("click", () => switchView("runs"));
$("nav-compare").addEventListener("click", () => switchView("compare"));
$("nav-history").addEventListener("click", () => switchView("history"));
$("nav-memory").addEventListener("click", () => switchView("memory"));
$("refresh").addEventListener("click", refresh);
$("compare-button").addEventListener("click", compare);
for (const id of ["search", "filter-author", "filter-environment", "filter-status"]) $(id).addEventListener("input", () => { state.table.page = 1; renderRuns(); });
$("page-prev").addEventListener("click", () => { state.table.page--; renderRuns(); });
$("page-next").addEventListener("click", () => { state.table.page++; renderRuns(); });
$("page-size").addEventListener("change", () => { state.table.pageSize = Number($("page-size").value); state.table.page = 1; renderRuns(); });
for (const key of runColumns) $("sort-" + key).addEventListener("click", () => {
  state.table.direction = state.table.sortKey === key ? (state.table.direction === "asc" ? "desc" : "asc") : (["score", "attempts", "updated_at"].includes(key) ? "desc" : "asc");
  state.table.sortKey = key; state.table.page = 1; renderRuns();
});
for (const id of ["baseline-select", "candidate-select"]) $(id).addEventListener("change", () => {
  $("comparison").hidden = true; $("comparison-empty").hidden = false; state.comparison = null;
});
$("detail-close").addEventListener("click", () => $("detail-dialog").close());
$("detail-dialog").addEventListener("close", () => { state.detail = null; state.detailRequest++; });
setInterval(() => { if (state.loggedIn && !document.hidden) refresh(); }, 5000);
document.addEventListener("visibilitychange", () => { if (!document.hidden && state.loggedIn) refresh(); });
globalThis.LoopDashboard?.init();
globalThis.ScoreHistory?.init();
globalThis.MemoryDashboard?.init();
refresh();
