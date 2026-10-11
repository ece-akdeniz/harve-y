"use strict";
globalThis.HarveyWorkspace = (() => {
  const $ = id => document.getElementById(id);
  const el = (tag, text, cls) => { const n = document.createElement(tag); if (text != null) n.textContent = String(text); if (cls) n.className = cls; return n; };
  const finite = v => typeof v === 'number' && Number.isFinite(v);
  const money = v => finite(v) ? new Intl.NumberFormat(undefined, {style:'currency',currency:'EUR',maximumFractionDigits:0}).format(v) : 'Not recorded';
  const number = v => finite(v) ? new Intl.NumberFormat(undefined,{maximumFractionDigits:1}).format(v) : '—';
  const date = v => v ? new Date(v).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : 'Not recorded';
  const label = v => String(v ?? 'Not recorded').replaceAll('_',' ');
  const state = {data:null, detail:null, tab:'conversation', request:0, signedIn:false, signature:'', busy:false};
  const route = () => {const p = location.hash.slice(1).split('/'); return {view:p[0] || 'overview',key:p[1],negotiation:p[2]};};
  const url = (s,n) => `#supplier/${encodeURIComponent(s.key)}/${encodeURIComponent(n.id)}`;
  const issue = n => n.stale || ['failed','interrupted'].includes(n.status) || n.must_haves_ok === false || (finite(n.timeouts) && n.timeouts > 0);
  const status = n => n.stale ? 'Update overdue' : n.must_haves_ok === false ? 'Requirements failed' : label(n.status);
  function reviewReason(n) {
    if (n.stale) return {label:'Update overdue', copy:'The source runner has not uploaded for over two minutes. Check the session state before acting.', priority:0};
    if (n.must_haves_ok === false) return {label:'Requirements failed', copy:'The recorded outcome missed a mandatory requirement. Inspect the terms and recovery evidence.', priority:1};
    if (finite(n.timeouts) && n.timeouts > 0) return {label:`${n.timeouts} timeout${n.timeouts === 1 ? '' : 's'} recorded`, copy:'Inspect the conversation and recovery evidence before reusing this result.', priority:2};
    if (['failed','interrupted'].includes(n.status)) return {label:label(n.status), copy:'Inspect the original failure and any recovered outcome before planning another move.', priority:3};
    return {label:'Review recorded outcome', copy:'Read the conversation and recorded evidence before applying this result.', priority:4};
  }
  function badge(text) { return el('span', text, 'badge'); }
  function panel(title, copy) {const n=el('section',null,'workspace-panel'); n.append(el('h3',title)); if(copy)n.append(el('p',copy)); return n;}
  function fields(value) {
    const dl=el('dl',null,'field-list');
    for(const [k,v] of Object.entries(value || {})) {dl.append(el('dt',label(k)),el('dd',format(k,v)));}
    return dl;
  }
  function format(k,v) {
    if(v==null)return 'Not recorded';
    if(typeof v === 'object')return JSON.stringify(v);
    if(typeof v === 'boolean')return v?'Yes':'No';
    if(k.endsWith('_days'))return `${number(v)} days`;
    if(k.endsWith('_months'))return `${number(v)} months`;
    if(k.includes('eur'))return money(v);
    if(k==='unit_price')return `${new Intl.NumberFormat(undefined,{style:'currency',currency:'EUR',maximumFractionDigits:4}).format(v)} / recorded price unit`;
    if(k==='ppm_commitment')return `${number(v)} ppm`;
    return String(v);
  }
  function disclosure(title,body,key) {const d=el('details'); if(key)d.dataset.keep=key; d.append(el('summary',title),body); return d;}
  function clearSession() {
    HarveyKnowledge.reset();
    state.request++; state.signedIn=false;state.data=null;state.detail=null;state.signature='';
    $('shell').hidden=true;$('sign-in').hidden=false;
    for(const id of ['supplier-content','supplier-list','attention','activity','decision-brief','operational-strip','supplier-summary','negotiation','knowledge-root'])$(id).replaceChildren();
    $('supplier-name').textContent='';$('supplier-meta').textContent='';
  }
  async function api(path,options={}) {
    const response=await fetch(path,{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(12000),...options});
    if(response.status===401){clearSession();throw new Error('Please sign in with the team password.');}
    if(!response.ok)throw new Error(`Workspace request failed (${response.status}).`);
    return response.json();
  }
  function activity(s,n,attention=false) {
    const a=el('a',null,attention ? 'activity-row triage-row' : 'activity-row evidence-row');a.href=url(s,n);
    const reason=reviewReason(n),meta=el('div',null,'activity-meta');
    meta.append(badge(attention ? reason.label : status(n)),el('span',`${n.case_id} · ${date(n.updated_at)}`));
    a.append(el('strong',s.name),meta);
    a.append(el('p',attention ? reason.copy : n.status==='completed' ? 'Completed negotiation with saved conversation and outcome evidence.' : `${status(n)} negotiation with saved conversation evidence.`));
    a.append(el('span',attention ? 'Open review →' : 'Open evidence →','row-action'));
    return a;
  }
  function emptyState(title, copy) {
    const box=el('div',null,'overview-empty');box.append(el('strong',title),el('p',copy));return box;
  }
  function overviewLoading() {
    const placeholder=className=>el('div',null,`overview-skeleton ${className}`);
    $('decision-brief').replaceChildren(placeholder('brief-skeleton'));
    $('operational-strip').replaceChildren(placeholder('strip-skeleton'));
    $('attention').replaceChildren(placeholder('rows-skeleton'));
    $('activity').replaceChildren(placeholder('rows-skeleton'));
    $('overview-status').textContent='Loading negotiation intelligence.';
  }
  function decisionBrief(d, rows, attention) {
    const s=d.summary,root=$('decision-brief');root.replaceChildren();
    const value=el('div',null,'value-story');
    value.append(el('span','Simulated cost reduction','value-label'),el('strong',finite(s.savings_eur)?money(s.savings_eur):'Not available','value-amount'));
    const coverage=finite(s.savings_eur)
      ? `${s.savings_covered} of ${s.savings_cases} latest cases have comparable valid outcomes${finite(s.savings_pct)?` · ${number(s.savings_pct)}% of recorded opening cost`:''}.`
      : `No comparable valid outcome is available across ${s.savings_cases} latest case${s.savings_cases === 1 ? '' : 's'}.`;
    value.append(el('p',coverage,'value-context'));
    const evidence=el('details',null,'brief-evidence');evidence.append(el('summary','View calculation basis'),el('p',d.savings_basis));value.append(evidence);
    const next=el('aside',null,'next-review');
    if(attention.length) {
      const {s:supplier,n}=attention[0],reason=reviewReason(n);
      next.append(el('span','Review next','next-label'),badge(reason.label),el('h2',supplier.name),el('p',`${n.case_id} · ${reason.copy}`));
      const link=el('a','Open negotiation →','button primary');link.href=url(supplier,n);next.append(link);
    } else if(rows.length) {
      const {s:supplier,n}=rows[0];
      next.append(el('span','Review next','next-label'),el('h2',supplier.name),el('p',`${n.case_id} is the latest recorded negotiation. Review its evidence before the next run.`));
      const link=el('a','Open latest evidence →','button primary');link.href=url(supplier,n);next.append(link);
    } else {
      next.append(el('span','Review next','next-label'),el('h2','Waiting for evidence'),el('p','Run a tracked negotiation to create the first supplier record for this environment.'));
    }
    root.append(value,next);
  }
  function operationalStrip(summary, attentionCount) {
    const root=$('operational-strip');root.replaceChildren();
    const entries=[
      ['Active sessions',summary.running,'Sessions still running'],
      ['Supplier coverage',summary.suppliers,'Suppliers with saved evidence'],
      ['Needs review',attentionCount,attentionCount ? 'Recorded issues require a check' : 'No recorded issues'],
    ];
    for(const [name,value,copy] of entries) {const item=el('div',null,'operational-item');item.append(el('span',name),el('strong',value),el('small',copy));root.append(item);}
  }
  function overview() {
    const d=state.data,s=d.summary;
    $('savings-basis').textContent=d.savings_basis;
    const rows=d.suppliers.flatMap(s=>s.negotiations.map(n=>({s,n}))).sort((a,b)=>b.n.updated_at.localeCompare(a.n.updated_at));
    const attention=rows.filter(({n})=>issue(n)).sort((a,b)=>reviewReason(a.n).priority-reviewReason(b.n).priority || b.n.updated_at.localeCompare(a.n.updated_at));
    decisionBrief(d,rows,attention);operationalStrip(s,attention.length);
    $('overview-status').textContent=`${attention.length} negotiation${attention.length === 1 ? '' : 's'} need${attention.length === 1 ? 's' : ''} review. ${s.suppliers} suppliers have saved evidence.`;
    $('attention').replaceChildren();
    attention.slice(0,6).forEach(({s,n})=>$('attention').append(activity(s,n,true)));
    if(!attention.length)$('attention').append(emptyState('No negotiations need review','There are no recorded failures, overdue updates, timeouts, or requirement violations in this environment.'));
    if(attention.length>6)$('attention').append(el('p',`Showing 6 of ${attention.length} supplier threads needing review. Open the supplier directory to see all.`, 'table-note'));
    const evidence=rows.filter(({n})=>!issue(n));$('activity').replaceChildren();
    evidence.slice(0,6).forEach(({s,n})=>$('activity').append(activity(s,n)));
    if(!rows.length)$('activity').append(emptyState('No evidence captured yet','Run a tracked negotiation and its conversation, outcome, and source context will appear here.'));
    else if(!evidence.length)$('activity').append(emptyState('Evidence is waiting for review','Resolve the listed issues before treating these negotiation records as learnings.'));
  }
  function directory() {
    if(!state.data)return;
    const query=$('supplier-search').value.toLowerCase(),filter=$('supplier-status').value;
    const suppliers=state.data.suppliers.filter(s=>`${s.name} ${s.supplier_id} ${s.negotiations.map(n=>n.case_id).join(' ')}`.toLowerCase().includes(query)
      &&(!filter || (filter==='running'?s.negotiations.some(n=>n.status==='running'):s.negotiations.some(issue))));
    $('supplier-count').textContent=`${suppliers.length} suppliers`;$('supplier-list').replaceChildren();
    for(const s of suppliers){
      const latest=s.negotiations[0],card=el('a',null,'supplier-card');card.href=url(s,latest);
      card.append(badge(s.negotiations.some(issue)?'Needs attention':status(latest)),el('h2',s.name),el('p',`${s.supplier_id} · ${s.arena_url}`,'muted'),el('p',[...new Set(s.negotiations.map(n=>n.case_id))].join(' · ')));
      const bottom=el('div',null,'supplier-bottom');bottom.append(el('span',`${s.negotiations.length} negotiations`),el('span','Open →'));card.append(bottom);$('supplier-list').append(card);
    }
    if(!suppliers.length)$('supplier-list').append(el('p','No matching suppliers. Try a different search, filter or environment.','notice'));
  }
  function nextSteps(d) {
    const box=panel('What to try next','Review guidance from recorded evidence. These suggestions do not change the agent’s policy or send a message.');
    const n=d.negotiation;
    if(n.stale)box.append(el('p','Check the runner connection and reconcile the session before continuing. The displayed conversation may be out of date.'));
    if(d.error)box.append(el('p',d.error,'error'));
    const findings=d.findings.filter(f=>f.category!=='keep');
    for(const f of findings.slice(0,5))box.append(el('p',f.observation),el('p',`Suggested check: ${f.next_test}`));
    if(!findings.length)box.append(el('p',n.status==='running'?'Review the latest supplier reply and unresolved terms. No saved next-action decision is available in this snapshot.':'Review offer changes and source-backed memory before planning a new negotiation. No tested supplier-specific next action is recorded.'));
    return box;
  }
  function decisionRecord(d) {
    const n=d.negotiation,record=el('section',null,'decision-record');
    const outcome=n.selected ? (n.deal ? 'Selected outcome' : 'Selected without a deal') : 'Recorded supplier thread';
    record.append(el('span',outcome,'record-label'),el('h3',`${n.case_id} · ${status(n)}`));
    const facts=el('div',null,'record-facts');
    facts.append(el('span',`${n.message_count} messages`),el('span',`Updated ${date(n.updated_at)}`));
    if(finite(n.score)) facts.append(el('span',`${number(n.score * 100)} / 100 case score`));
    record.append(facts);
    if(n.savings) record.append(el('p',`${money(n.savings.change_eur)} simulated reduction from the recorded case opening full cost.`));
    else record.append(el('p','This thread has saved evidence, but no comparable valid savings outcome is available.'));
    return record;
  }
  function conversation(d) {
    const layout=el('div',null,'negotiation-layout'),main=el('div'),aside=el('aside',null,'decision-aside');
    const digest=el('section',null,'workspace-panel conversation-digest');digest.append(el('h3','What changed in this negotiation'));
    (d.digest?.summary || []).forEach(item=>digest.append(el('p',item.text)));
    main.append(decisionRecord(d),digest,HarveyConversations.render(d));
    const outcome=panel('Current recorded position');outcome.append(fields({session_status:status(d.negotiation),supplier_thread:d.thread_status,selected_supplier:d.negotiation.selected,must_haves_satisfied:d.negotiation.must_haves_ok}));
    if(d.negotiation.savings)outcome.append(el('p',`${money(d.negotiation.savings.change_eur)} simulated reduction from case opening full cost.`));
    aside.append(outcome,nextSteps(d));layout.append(main,aside);return layout;
  }
  function offers(d) {
    const root=el('div'),sheets=d.messages.filter(m=>m.from!=='buyer').flatMap(m=>Array.isArray(m.term_sheets)?m.term_sheets:[]).filter(s=>s?.terms);
    const first=sheets[0]?.terms || {},last=sheets.at(-1)?.terms || {},final=d.result.terms || {};
    const box=panel('How the terms changed','Supplier sheets are recorded proposals. They may omit defaults from quote attachments; this view does not revalidate whether a historical offer can still be accepted.');
    const wrap=el('div',null,'table-shell'),table=el('table',null,'offer-table'),head=el('thead'),tr=el('tr');
    ['Criterion','First supplier sheet','Latest supplier sheet','Final selected terms'].forEach(t=>tr.append(el('th',t)));head.append(tr);table.append(head);const body=el('tbody');
    const keys=[...new Set([...Object.keys(first),...Object.keys(last),...Object.keys(final)])];
    for(const k of keys){const row=el('tr');row.append(el('th',label(k)),... [first,last,final].map(v=>el('td',format(k,v[k]))));body.append(row);}table.append(body);wrap.append(table);
    if(keys.length)box.append(wrap);else box.append(el('p','No structured terms were included in this snapshot.'));
    root.append(box);
    const outcome=panel('Complete cost & mandatory requirements');
    outcome.append(fields({opening_full_cost_eur:d.result.c_open,outcome_full_cost_eur:d.result.c_deal,must_haves_satisfied:d.result.must_haves_ok}));
    outcome.append(el('p','Opening cost is the recorded case baseline and may belong to a different RFQ supplier. Detailed requirement thresholds are not included in these saved run snapshots. Unknown requirements are not treated as satisfied.'));
    if(d.result.cost_breakdown)outcome.append(disclosure('Recorded cost components',fields(d.result.cost_breakdown),'costs'));
    if(d.result.reconciled_result || d.recovery)outcome.append(disclosure('Recovered outcome · original failure retained',el('pre',JSON.stringify(d.result.reconciled_result || d.recovery,null,2)),'recovery'));
    root.append(outcome);return root;
  }
  function memory(d) {
    const root=el('div',null,'memory-columns');
    const facts=panel('Versioned supplier facts',`${d.memory.fact_count} source records in the matching supplied data version. Showing up to 100. Dates and validity remain part of each source; these are not proof the agent used them.`);
    if(!d.memory.fact_count)facts.append(el('p','No matching supplier facts registered for this run’s data version.'));
    d.memory.facts.forEach((f,i)=>facts.append(disclosure(`${f.source_id} · ${f.layer || 'source layer unknown'}`,fields(f.values),`fact-${i}`)));
    const obs=panel('Conversation memory',`${d.memory.observation_count} observations for this supplier, case, environment and data version. Showing up to 100. History includes later sessions; it is not a reconstruction of the agent’s input.`);
    if(!d.memory.observation_count)obs.append(el('p','No source-matched observations available. Unknown data versions are kept separate.'));
    d.memory.observations.forEach((o,i)=>{const source=el('div');source.append(el('p',o.excerpt || 'Structured offer observation'),el('p',`${o.citation.case_id} · session ${o.citation.session_id} · message ${o.citation.message_index+1}`,'memory-source'));obs.append(disclosure(`${label(o.kind)} · ${label(o.field)} · ${o.direction || o.value}`,source,`memory-${i}`));});
    obs.append(el('p','Observations describe what happened. They are not approved policy or evidence of a stable supplier preference.'));
    root.append(facts,obs);return root;
  }
  function policy(d) {
    const root=el('div',null,'memory-columns'),p=panel('Policy recorded for this negotiation','This is the saved run configuration. It does not establish which policy is currently deployed or authorize a change.');
    p.append(fields({agent:d.policy.agent,source:d.policy.source,commit:d.policy.provenance?.commit || 'Unknown',data_version:d.policy.provenance?.data_sha256 || 'Unknown'}));
    if(Object.keys(d.policy.config || {}).length)p.append(disclosure('Recorded configuration',fields(d.policy.config),'policy-config'));
    else p.append(el('p','The original configuration was not recorded.'));
    const memoryConfig=Object.entries(d.policy.config || {}).filter(([key])=>key.includes('memory'));
    p.append(el('p',memoryConfig.length?'Memory settings are recorded below; this snapshot does not contain a per-decision retrieval trace.':'No memory selection is recorded in this configuration. Displayed supplier history does not imply runtime use.'));
    if(memoryConfig.length)p.append(fields(Object.fromEntries(memoryConfig)));
    root.append(p,nextSteps(d));return root;
  }
  function supplier(d) {
    state.detail=d;
    const s=state.data.suppliers.find(s=>s.key===d.key);
    $('supplier-name').textContent=s?.name || d.supplier_id;
    $('supplier-meta').textContent=`${d.supplier_id} · ${d.negotiation.environment} · ${d.negotiation.arena_url}`;
    $('negotiation').replaceChildren();
    for(const n of d.negotiations){const o=el('option',`${n.case_id} · ${date(n.started_at)} · ${label(n.status)} · ${n.id.slice(-6)}`);o.value=n.id;$('negotiation').append(o);}$('negotiation').value=d.negotiation.id;
    $('supplier-summary').replaceChildren(badge(status(d.negotiation)),badge(d.negotiation.case_id),badge(finite(d.negotiation.score)?`${number(d.negotiation.score*100)} / 100 · case score`:'Case score not attributed'),el('span',`Source updated ${date(d.negotiation.updated_at)} · ${d.negotiation.message_count} messages`,'muted small'));
    renderTab();
  }
  function renderTab() {
    if(!state.detail)return;
    const content=$('supplier-content'),open=new Set([...content.querySelectorAll('details[open]')].map(d=>d.dataset.keep));
    if(state.tab==='knowledge'){
      let host=content.querySelector('.supplier-knowledge');
      if(!host){host=el('div',null,'supplier-knowledge');content.replaceChildren(host);}
      HarveyKnowledge.load({host,api,environment:state.detail.negotiation.environment,supplier:state.detail.supplier_id,arena:state.detail.negotiation.arena_url});
    } else {HarveyKnowledge.reset();content.replaceChildren(({conversation,offers,memory,policy}[state.tab])(state.detail));}
    content.querySelectorAll('details').forEach(d=>{if(open.has(d.dataset.keep))d.open=true;});
    $('tabs').querySelectorAll('button').forEach(b=>b.setAttribute('aria-current',b.dataset.tab===state.tab?'page':'false'));
  }
  function showRoute() {
    const r=route(),view=r.view==='supplier'?'supplier':r.view==='suppliers'?'suppliers':r.view==='knowledge'?'knowledge':'overview';
    for(const v of ['overview','suppliers','supplier','knowledge'])$(v+'-view').hidden=v!==view;
    $('breadcrumb').textContent=view==='overview'?'Overview':view==='knowledge'?'Shared knowledge':'Suppliers';
    $('page-title').textContent=view==='overview'?'Negotiation Intelligence Lab':view==='suppliers'?'Your suppliers':view==='knowledge'?'Supplier intelligence':'Supplier workspace';
    $('page-subtitle').textContent=view==='overview'?'See what Harvey learned, where value changed, and what deserves review next.':view==='suppliers'?'Choose a supplier to review conversations, offers and results.':view==='knowledge'?'Choose a supplier. Read the brief. Prepare your next negotiation.':'Review the latest exchange or open Shared knowledge for the full relationship.';
    for(const v of ['overview','suppliers','knowledge']){$('nav-'+v).classList.toggle('active',v===(view==='supplier'?'suppliers':view));$('nav-'+v).setAttribute('aria-current',v===(view==='supplier'?'suppliers':view)?'page':'false');}
  }
  async function refresh() {
    const request=++state.request,r=route();state.busy=true;
    try {
      const data=await api(`/api/workspace?environment=${encodeURIComponent($('environment').value)}`);
      if(request!==state.request)return;
      state.data=data;state.signedIn=true;$('sign-in').hidden=true;$('shell').hidden=false;$('error').hidden=true;
      overview();directory();showRoute();
      if(r.view==='supplier' && r.key) {
        const d=await api(`/api/workspace/suppliers/${encodeURIComponent(r.key)}${r.negotiation?`?negotiation=${encodeURIComponent(r.negotiation)}`:''}`);
        if(request!==state.request)return;
        if($('environment').value!==d.negotiation.environment){
          $('environment').value=d.negotiation.environment;
          const scoped=await api(`/api/workspace?environment=${encodeURIComponent(d.negotiation.environment)}`);
          if(request!==state.request)return;
          state.data=scoped;overview();directory();
        }
        const signature=JSON.stringify(d);
        if(signature!==state.signature){supplier(d);state.signature=signature;}
      }
      if(r.view==='knowledge')await HarveyKnowledge.load({host:$('knowledge-root'),api,environment:$('environment').value});
      if(r.view==='supplier' && state.tab==='knowledge' && state.detail)renderTab();
      if(request!==state.request)return;
      $('connection').textContent=`Connected · checked ${date(new Date().toISOString())}`;
    } catch(error) {
      if(request!==state.request)return;
      if(!state.signedIn){$('sign-in').hidden=false;$('login-error').textContent=error.message;}
      $('connection').textContent='Disconnected · showing saved view';$('error').hidden=false;$('error').textContent=`Could not refresh. ${error.message}`;
    } finally {if(request===state.request)state.busy=false;}
  }
  async function logout() {try{await api('/api/logout',{method:'POST'});}catch{} clearSession();state.busy=false;}
  function init() {
    $('sign-in-form').addEventListener('submit',async event=>{event.preventDefault();const button=event.currentTarget.querySelector('button');button.disabled=true;
      try{await api('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:$('password').value})});$('password').value='';$('login-error').textContent='';await refresh();}
      catch(error){$('login-error').textContent=error.message;}finally{button.disabled=false;}});
    for(const id of ['logout','mobile-logout'])$(id).addEventListener('click',logout);
    $('refresh').addEventListener('click',()=>{HarveyKnowledge.reset();refresh();});
    $('environment').addEventListener('change',()=>{
      HarveyKnowledge.reset();state.signature='';state.data=null;state.detail=null;
      $('supplier-list').replaceChildren();overviewLoading();
      $('supplier-count').textContent='Loading suppliers…';
      location.hash='overview';refresh();
    });
    $('supplier-search').addEventListener('input',directory);$('supplier-status').addEventListener('change',directory);
    $('negotiation').addEventListener('change',()=>{if(state.detail)location.hash=url({key:state.detail.key},{id:$('negotiation').value});});
    $('tabs').addEventListener('click',e=>{const tab=e.target.dataset.tab;if(tab){state.tab=tab;renderTab();}});
    window.addEventListener('hashchange',()=>{HarveyKnowledge.reset();state.signature='';state.detail=null;$('supplier-content').replaceChildren(el('p','Loading negotiation…','notice'));showRoute();refresh();});
    document.addEventListener('visibilitychange',()=>{if(!document.hidden && state.signedIn)refresh();});
    setInterval(()=>{if(!document.hidden && state.signedIn && !state.busy)refresh();},5000);
    refresh();
  }
  return {init,format,issue,overview,directory,supplier,state,clearSession,refresh,renderTab};
})();
HarveyWorkspace.init();
