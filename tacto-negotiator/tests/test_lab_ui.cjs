const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function page(fetch) {
  const nodes = new Map();
  const document = {
    hidden: false,
    getElementById(id) {
      if (!nodes.has(id)) nodes.set(id, {
        textContent: '', hidden: false, open: false, value: '',
        addEventListener() {}, replaceChildren() {},
      });
      return nodes.get(id);
    },
    addEventListener() {},
  };
  const context = vm.createContext({ document, fetch, Intl, AbortSignal, setInterval() {} });
  document.getElementById('login-error');
  const source = fs.readFileSync(path.join(__dirname, '../src/negotiator/lab/static/app.js'), 'utf8');
  vm.runInContext(source.replace(/refresh\(\);\s*$/, ''), context);
  return { context, nodes };
}

test('connection failures show a useful error on the login screen', async () => {
  const { context, nodes } = page(async () => { throw new TypeError('Failed to fetch'); });
  await vm.runInContext('refresh()', context);
  assert.match(nodes.get('login-error').textContent, /Could not connect/);
  assert.doesNotMatch(nodes.get('login-error').textContent, /^Sign in to connect/);
});

test('a missing session immediately after login is reported instead of swallowed', async () => {
  const { context } = page(async () => ({ ok: false, status: 401, json: async () => ({ error: 'authentication required' }) }));
  await assert.rejects(vm.runInContext('refresh({ afterLogin: true })', context), /session cookie/);
});

test('HTML from a tunnel is rejected instead of treated as dashboard data', async () => {
  const { context } = page(async () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError('Unexpected token'); } }));
  await assert.rejects(vm.runInContext('api("/api/runs")', context), /unexpected response/);
});

test('an anonymous first visit does not show an error', async () => {
  const { context, nodes } = page(async () => ({ ok: false, status: 401, json: async () => ({ error: 'authentication required' }) }));
  await vm.runInContext('refresh()', context);
  assert.equal(nodes.get('login-error').textContent, '');
});

test('sign-in waits for an earlier anonymous refresh and checks the new session', async () => {
  let release;
  const firstResponse = new Promise(resolve => { release = resolve; });
  let calls = 0;
  const unauthorized = { ok: false, status: 401, json: async () => ({ error: 'authentication required' }) };
  const { context } = page(async () => ++calls === 1 ? firstResponse : unauthorized);
  const initial = vm.runInContext('refresh()', context);
  const signedIn = vm.runInContext('refresh({ afterLogin: true })', context);
  const checked = assert.rejects(signedIn, /session cookie/);
  release(unauthorized);
  await initial;
  await checked;
  assert.equal(calls, 2);
});

test('report summary preserves incomplete outcomes and unknown timeouts', () => {
  const { context } = page(async () => {});
  context.attempts = [
    { status: 'completed', score: 0.8, elapsed_s: 10, timeouts: 0, result: { deal: true } },
    { status: 'failed', score: null, elapsed_s: 5, timeouts: null, result: { reconciled_result: { score: 1 } } },
  ];
  const value = vm.runInContext('reportMetrics(attempts)', context);
  assert.equal(value.mean, 0.8);
  assert.equal(value.partial, true);
  assert.equal(value.completed, 1);
  assert.equal(value.deals, 1);
  assert.equal(value.timeouts, null);
  assert.equal(value.duration, 15);
});

test('lab campaigns become sortable experiment rows with paired scores and attempt counts', () => {
  const { context } = page(async () => {});
  context.payload = {suites: [{suite_id: 'async', environment: 'sandbox'}], campaigns: [
    {campaign_id: 'comparison', suite_id: 'async', author: 'ece', status: 'rejected',
      hypothesis: 'conditional anchor', created_at: 1791663600,
      attempt_counts: {completed: 12, total: 12, failed: 0},
      completion: {evaluation: {cases: [
        {baseline: {mean: 90}, candidate: {mean: 90}},
        {baseline: {mean: 40}, candidate: {mean: 50}},
      ], metrics: {gain: 5}}}},
  ]};
  const rows = vm.runInContext('campaignRows(payload)', context);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].run_id, 'campaign:comparison');
  assert.equal(rows[0].environment, 'sandbox');
  assert.equal(rows[0].metrics.mean_score, 0.7);
  assert.equal(rows[0].metrics.baseline_mean, 0.65);
  assert.equal(rows[0].metrics.completed, 12);
  assert.equal(rows[0].metrics.gain_points, 5);
  context.rows = rows;
  assert.equal(vm.runInContext('experimentPage(rows, {query: "comparison"}).total', context), 1);
});

test('readable fields distinguish units, disabled options, zero and missing values', () => {
  const { context } = page(async () => {});
  for (const [key, value, expected] of [
    ['payment_days', 30, '30 days'], ['contract_months', 24, '24 months'],
    ['claims', false, 'Disabled'], ['anchor', 0.12, '12%'],
    ['lead_time_days', null, 'Not recorded'], ['tooling_eur', 0, '€0.00'],
  ]) {
    context.input = { key, value };
    assert.equal(vm.runInContext('formatField(input.key, input.value)', context), expected);
  }
});

test('supplier conversations retain separate message order and buyer roles', () => {
  const { context } = page(async () => {});
  context.thread = { messages: [
    { from: 'sales@example.test', from_name: 'Supplier A', body: '<script>unsafe</script>' },
    { from: 'buyer', body: 'Our counter', term_sheets: [{ terms: { unit_price: 10 } }] },
  ] };
  const messages = vm.runInContext('threadMessages(thread)', context);
  assert.equal(messages.length, 2);
  assert.equal(messages[0].body, '<script>unsafe</script>');
  assert.equal(messages[1].from, 'buyer');
  assert.equal(messages[1].term_sheets[0].terms.unit_price, 10);
  assert.equal(vm.runInContext('threadMessages({ evidence_truncated: true }).length', context), 0);
});

test('closing actions display their type for both arena objects and legacy strings', () => {
  const { context } = page(async () => {});
  assert.equal(vm.runInContext('actionLabel({ type: "accept", term_sheet_id: "offer:1" })', context), 'Accept');
  assert.equal(vm.runInContext('actionLabel({ type: "walk_away" })', context), 'Walk away');
  assert.equal(vm.runInContext('actionLabel("accept")', context), 'Accept');
});

test('an in-flight background refresh cannot reopen a dismissed report', async () => {
  let release;
  const response = new Promise(resolve => { release = resolve; });
  const { context, nodes } = page(() => response);
  let opens = 0;
  context.renderDetail = () => {};
  vm.runInContext('state.loggedIn = true; state.detail = { run_id: "run-one" };', context);
  const dialog = nodes.get('detail-dialog'); dialog.open = true;
  dialog.showModal = () => { opens++; };
  const request = vm.runInContext('openDetail("run-one", { background: true })', context);
  dialog.open = false;
  vm.runInContext('state.detail = null', context);
  release({ ok: true, status: 200, json: async () => ({ run_id: 'run-one' }) });
  await request;
  assert.equal(opens, 0);
  assert.equal(vm.runInContext('state.detail', context), null);
});

// Loop presentation tests share this entry point; DOM smoke is opt-in via LAB_UI_DOM_MODULE.
require('./test_lab_loop_ui.cjs');

test('experiment sorting spans pages, sorts scores numerically and keeps unknowns last', () => {
  const {context} = page(async () => {});
  context.rows = [
    {run_id:'missing', name:'Unknown', metrics:{}},
    {run_id:'low', name:'Run 10', metrics:{mean_score:0}},
    {run_id:'high', name:'Run 2', metrics:{mean_score:.9}},
    {run_id:'partial', name:'Run 3', metrics:{mean_score:null,observed_mean:.12}},
  ];
  assert.equal(vm.runInContext('typeof experimentPage',context),'function');
  const result = vm.runInContext('experimentPage(rows, {page:2, pageSize:2, sortKey:"score", direction:"desc"})',context);
  assert.deepEqual(Array.from(result.rows,r=>r.run_id),['low','missing']);
  assert.equal(result.total,4);
  assert.deepEqual(Array.from(vm.runInContext('experimentPage(rows,{pageSize:10,sortKey:"score",direction:"asc"}).rows',context),r=>r.run_id),['low','partial','high','missing']);
  assert.deepEqual(Array.from(vm.runInContext('experimentPage(rows,{pageSize:10,sortKey:"name",direction:"asc"}).rows',context),r=>r.run_id),['high','partial','low','missing']);
});

test('filtering precedes pagination and invalid pages clamp without mutating incoming data', () => {
  const {context} = page(async () => {});
  context.rows = Array.from({length:60},(_,i)=>({run_id:String(i),name:'Test '+i,author:i%2?'Baris':'Other',environment:'sandbox',status:'completed',updated_at:`2026-10-10T12:00:${String(i).padStart(2,'0')}Z`,metrics:{completed:i,planned:60}}));
  assert.equal(vm.runInContext('typeof experimentPage',context),'function');
  const result = vm.runInContext('experimentPage(rows,{page:9,pageSize:25,author:"Baris",sortKey:"updated_at",direction:"desc"})',context);
  assert.equal(result.page,2); assert.equal(result.total,30); assert.equal(result.pages,2);
  assert.deepEqual(Array.from(result.rows,r=>r.run_id),['9','7','5','3','1']);
  assert.equal(context.rows[0].run_id,'0');
  const empty = vm.runInContext('experimentPage(rows,{query:"absent",page:8})',context);
  assert.equal(empty.page,1); assert.equal(empty.rows.length,0); assert.equal(empty.total,0);
});
