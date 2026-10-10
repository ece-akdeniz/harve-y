"use strict";
// Authenticated inspection only. Supplier evidence always enters the DOM as text.
globalThis.MemoryDashboard = (() => {
  const $ = id => document.getElementById(id);
  const node = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text != null) n.textContent = String(text);
    if (cls) n.className = cls;
    return n;
  };
  const label = value => String(value ?? 'Unknown').replaceAll('_', ' ');
  let graph = null, snapshots = [], currentPage = 1, request = 0, signature = '';
  function page(observations, filters = {}, index = 1) {
    const rows = observations.filter(o => (!filters.supplier || o.citation.supplier === filters.supplier)
      && (!filters.case || o.citation.case_id === filters.case)
      && (!filters.environment || o.citation.environment === filters.environment));
    const pages = Math.max(1, Math.ceil(rows.length / 25));
    const number = Math.max(1, Math.min(index, pages));
    return {rows: rows.slice((number - 1) * 25, number * 25), total: rows.length, pages, number};
  }
  function details(title, children) {
    const d = node('details');
    d.append(node('summary', title), ...children);
    return d;
  }
  function citation(observation) {
    const c = observation.citation;
    const text = `${c.arena_url} · ${c.environment} · ${c.case_id} · ${c.supplier} · ${c.session_id} · ${c.attempt_id} · message ${c.message_index}`;
    const children = [node('p', text, 'memory-citation'), node('p', observation.excerpt, 'message-body'),
      node('p', `Evidence ${observation.evidence_id} · message SHA256 ${c.message_sha256}`, 'evidence-id')];
    if (c.run_id || c.campaign_id) {
      const button = node('button', c.run_id ? `Inspect run ${c.run_id}` : `Inspect campaign ${c.campaign_id}`, 'button secondary');
      button.type = 'button';
      button.addEventListener('click', () => {
        if (!state.loggedIn) return;
        if (c.run_id) openDetail(c.run_id);
        else globalThis.LoopDashboard?.openCampaign(c.campaign_id);
      });
      children.push(button);
    }
    return details('Source citation and supplier text', children);
  }
  function support(ids, observations) {
    const lookup = new Map(observations.map(o => [o.evidence_id, o]));
    return details(`${ids.length} supporting citations`, ids.map(id => lookup.has(id)
      ? citation(lookup.get(id)) : node('p', `Evidence ${id} · source unavailable in this graph`, 'evidence-id')));
  }
  function fillOptions(id, values, placeholder) {
    const select = $(id), previous = select.value;
    const entries = [...new Set(values)].sort();
    select.replaceChildren();
    for (const value of ['', ...entries]) {
      const option = node('option', value || placeholder); option.value = value; select.append(option);
    }
    select.value = entries.includes(previous) ? previous : '';
  }
  function renderObservations() {
    if (!graph) return;
    const result = page(graph.observations || [], {supplier: $('memory-supplier').value,
      case: $('memory-case').value, environment: $('memory-environment').value}, currentPage);
    currentPage = result.number;
    const root = $('memory-observations'); root.replaceChildren();
    for (const observation of result.rows) {
      const c = observation.citation, card = node('article', null, 'panel memory-card');
      card.append(node('h4', c.supplier), node('p', `${label(observation.kind)} · ${label(observation.field)} · ${observation.direction ? label(observation.direction) : observation.value}`),
        node('p', `${c.case_id} · ${c.environment} · ${c.arena_url}`, 'muted small'), citation(observation));
      root.append(card);
    }
    if (!result.total) root.append(node('p', 'No matching original supplier observations.', 'notice'));
    const start = result.total ? (result.number - 1) * 25 + 1 : 0;
    $('memory-range').textContent = `${start}–${Math.min(result.number * 25, result.total)} of ${result.total} observations · 25 per page`;
    $('memory-position').textContent = `${result.number} / ${result.pages}`;
    $('memory-prev').disabled = result.number <= 1;
    $('memory-next').disabled = result.number >= result.pages;
  }
  function render(data, frozen) {
    graph = data; snapshots = frozen;
    const observations = data.observations || [], coverage = data.coverage || {};
    $('memory-coverage').textContent = `${coverage.session_count ?? 0} original sessions · ${coverage.supplier_count ?? 0} suppliers · ${coverage.case_count ?? 0} cases · ${observations.length} observations`;
    const lessons = $('memory-lessons'); lessons.replaceChildren();
    if (!(data.lessons || []).length) lessons.append(node('p', 'Insufficient evidence for general lessons. At least three distinct suppliers across two cases with consistent explicit statements are required. Offers alone do not teach a preference; missing or conflicting evidence abstains.', 'notice'));
    for (const lesson of data.lessons || []) {
      const card = node('article', null, 'panel memory-card');
      card.append(node('h4', `${label(lesson.field)} · prefer ${lesson.direction}`),
        node('p', `${lesson.supporting_suppliers.length} suppliers · ${lesson.supporting_cases.length} cases`, 'memory-support'),
        node('p', 'Candidate lesson · requires separate held-out evaluation. No measured score gain is implied.', 'muted small'),
        node('p', `${lesson.arena_url} · ${lesson.environment}`, 'muted small'),
        node('p', 'Applies only among currently valid packages of no greater buyer cost. Unsupported contexts abstain.'),
        support(lesson.evidence_ids || [], observations));
      lessons.append(card);
    }
    for (const conflict of data.conflicts || []) {
      const card = node('article', null, 'panel memory-card memory-conflict');
      card.append(node('h4', `Conflict · ${label(conflict.field)} · abstains`),
        node('p', 'Opposing supplier statements suppress this lesson.'),
        node('p', `${conflict.arena_url} · ${conflict.environment}`, 'muted small'),
        support(conflict.evidence_ids || [], observations));
      lessons.append(card);
    }
    fillOptions('memory-supplier', observations.map(o => o.citation.supplier), 'All suppliers');
    fillOptions('memory-case', observations.map(o => o.citation.case_id), 'All cases');
    fillOptions('memory-environment', observations.map(o => o.citation.environment), 'All environments');
    renderObservations();
    const list = $('memory-snapshots'); list.replaceChildren();
    if (!snapshots.length) list.append(node('p', 'No frozen snapshots. Build an explicitly scoped discovery candidate with the authenticated lab CLI.', 'notice'));
    for (const snapshot of snapshots) {
      const card = node('article', null, 'panel memory-card');
      card.append(node('h4', snapshot.snapshot_id, 'evidence-id'),
        node('p', `${snapshot.lessons.length ? 'Candidate snapshot · held-out evaluation required' : 'Abstains · no qualified lessons'} · ${snapshot.lessons.length} lessons`),
        node('p', `${snapshot.arena_url} · ${snapshot.environment}`, 'muted small'),
        details('Frozen discovery cohort', [node('p', `Cases: ${snapshot.source_cases.join(', ')}`),
          node('p', `Suppliers: ${snapshot.source_suppliers.join(', ') || 'None'}`),
          node('p', `Sessions: ${snapshot.source_sessions.join(', ')}`)]));
      list.append(card);
    }
  }
  function reset() {
    request++; graph = null; snapshots = []; currentPage = 1; signature = '';
    for (const id of ['memory-lessons', 'memory-observations', 'memory-snapshots']) $(id)?.replaceChildren();
    for (const id of ['memory-error', 'memory-coverage', 'memory-range', 'memory-position']) if ($(id)) $(id).textContent = '';
    for (const [id, text] of [['memory-supplier', 'All suppliers'], ['memory-case', 'All cases'], ['memory-environment', 'All environments']]) if ($(id)) fillOptions(id, [], text);
    if ($('memory-prev')) $('memory-prev').disabled = true;
    if ($('memory-next')) $('memory-next').disabled = true;
  }
  async function refresh() {
    if (!state.loggedIn) return;
    const generation = state.memoryGeneration, revision = ++request;
    try {
      const [data, frozen] = await Promise.all([api('/api/loop/memory'), api('/api/loop/memory-snapshots')]);
      if (generation !== state.memoryGeneration || revision !== request || !state.loggedIn) return;
      $('memory-error').textContent = '';
      const next = JSON.stringify([data, frozen]);
      if (signature !== next) { render(data, frozen['memory-snapshots'] || []); signature = next; }
    } catch (error) {
      if (generation === state.memoryGeneration && revision === request && state.loggedIn)
        $('memory-error').textContent = `Could not refresh memory evidence. ${error.message}`;
    }
  }
  function init() {
    for (const id of ['memory-supplier', 'memory-case', 'memory-environment']) $(id).addEventListener('change', () => { currentPage = 1; renderObservations(); });
    $('memory-prev').addEventListener('click', () => { currentPage--; renderObservations(); });
    $('memory-next').addEventListener('click', () => { currentPage++; renderObservations(); });
    $('memory-clear').addEventListener('click', () => {
      for (const id of ['memory-supplier', 'memory-case', 'memory-environment']) $(id).value = '';
      currentPage = 1; renderObservations();
    });
  }
  return {page, render, refresh, reset, init};
})();
