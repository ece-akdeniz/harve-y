"use strict";
globalThis.HarveyBrief = (() => {
  const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!=null)n.textContent=String(text);if(cls)n.className=cls;return n;};
  const label=v=>String(v ?? 'Unknown').replaceAll('_',' ');
  const date=v=>v?new Date(v).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'}):'Unknown date';
  const money=v=>typeof v==='number'?new Intl.NumberFormat(undefined,{style:'currency',currency:'EUR',maximumFractionDigits:0}).format(v):'Unavailable';
  function evidence(item,actions){
    const links=el('div',null,'brief-evidence');
    if(item.node_id){const b=el('button','Inspect shared memory ↗','text-button');b.onclick=()=>actions.inspect(item.node_id);links.append(b);}
    (item.evidence || []).slice(0,3).forEach((ref,i)=>{const b=el('button',`${ref.case_id}${ref.message_index!=null?` · message ${ref.message_index+1}`:' · outcome'} ↗`,'text-button');b.title=`Source ${i+1} · ${ref.session_id || ref.negotiation_id}`;b.onclick=()=>actions.open(ref);links.append(b);});
    return links;
  }
  function card(item,actions){const c=el('article',null,'brief-item');if(item.status)c.append(el('span',item.status,'badge'));c.append(el('h4',item.title),el('p',item.text));const refs=evidence(item,actions);if(refs.childNodes.length){const d=el('details',null,'inline-evidence');d.append(el('summary','View evidence'),refs);c.append(d);}return c;}
  function section(title,items,actions,empty){const box=el('section',null,'workspace-panel brief-section');box.append(el('h3',title));if(!items.length)box.append(el('p',empty,'muted'));items.forEach(i=>box.append(card(i,actions)));return box;}
  function render(report,actions){
    const root=el('div',null,'supplier-brief');
    if(!report.partitions.length){root.append(el('section',null,'workspace-panel'));root.firstChild.append(el('h2','A new relationship starts here.'),el('p','There are no matching saved negotiations in this dataset and environment. The graph contains the supplied supplier facts. Once a run is saved, its conversation, outcomes and observations will appear here.'),el('p','Suggested preparation: review the latest supplied facts, confirm requirements and request a current offer. No supplier-specific policy has been established.'));return root;}
    let selected=report.partitions.find(p=>p.id===actions.partition)?.id || report.partitions[0].id;
    const content=el('div');
    if(report.partitions.length>1){const wrap=el('label','Analyze one evidence partition','partition-picker'),picker=el('select');picker.setAttribute('aria-label','Report evidence partition');report.partitions.forEach(p=>{const o=el('option',`${p.dataset.startsWith('unknown:')?'Unregistered source · '+p.dataset.slice(8):'Dataset '+p.dataset.slice(0,12)} · ${p.stats.sessions} negotiations · ${p.arena}`);o.value=p.id;picker.append(o);});picker.value=selected;picker.onchange=()=>{selected=picker.value;draw();};wrap.append(picker);root.append(wrap,el('p',report.boundary,'table-note'));}
    root.append(content);
    function draw(){
      const p=report.partitions.find(p=>p.id===selected);actions.partition=selected;content.replaceChildren();
      const hero=el('section',null,'brief-hero');hero.append(el('h2','Relationship at a glance'),el('p',p.summary,'brief-lead'),el('p',`${date(p.period.first)} — ${date(p.period.last)} · ${p.stats.messages} saved messages · evidence-based brief`,'muted small'));
      const stats=el('div',null,'brief-stats');for(const [value,name] of [[`${p.stats.valid_deals} / ${p.stats.sessions}`,'confirmed deals'],[p.stats.other_selected,'other suppliers chosen'],[money(p.stats.latest_case_reduction_eur),'simulated cost reduction']]){const x=el('div');x.append(el('strong',value),el('span',name));stats.append(x);}hero.append(stats);const metricNote=el('details',null,'metric-definition');metricNote.append(el('summary','How these numbers are calculated'),el('p',`Cost coverage: ${p.stats.cost_coverage} / ${p.stats.cases} latest cases. Repeats are not added together. The opening baseline can be a different RFQ supplier.`,'table-note'));hero.append(metricNote);const heroRow=el('div',null,'brief-priority-row'),next=el('section',null,'next-priority');next.append(el('span','Suggested next step','priority-label'));if(p.next_steps[0])next.append(card(p.next_steps[0],actions));const cta=el('button','Review latest conversation','button primary');cta.onclick=()=>actions.open(p.latest.reference);next.append(cta);heroRow.append(hero,next);content.append(heroRow);
      const latest=el('details',null,'workspace-panel latest-exchange');latest.append(el('summary',`Latest conversation summary · ${p.latest.case_id}`));
      p.latest.summary.forEach(i=>{const row=el('div',null,'digest-beat');row.append(el('p',i.text),evidence(i,actions));latest.append(row);});
      if(p.latest.truncated)latest.append(el('p','The original conversation upload was truncated.','notice'));

      const columns=el('div',null,'brief-columns');columns.append(section('What to remember',p.memory.slice(0,2),actions,'No supplier preferences or comparable offers recorded yet.'),section('How to approach them',p.approach.slice(0,2),actions,''));content.append(columns);
      const topics=el('details',null,'workspace-panel brief-topics');topics.append(el('summary',`Conversation themes · ${p.topics.length} topics`),el('p','Quoted supplier replies, grouped by topic. Mentions do not establish preferences.','muted'));
      if(!p.topics.length)topics.append(el('p','No supported topics could be extracted from the saved supplier replies.'));
      p.topics.forEach(t=>{const item=el('details');item.append(el('summary',`${t.title} · ${t.count} conversations`));item.append(el('p',t.text));t.evidence.forEach(ref=>{item.append(el('blockquote',ref.quote),evidence({evidence:[ref]},actions));});topics.append(item);});const more=el('details',null,'workspace-panel brief-more');more.append(el('summary','More memory & follow-up ideas'),section('Shared memory',p.memory.slice(2),actions,'All available memory is shown above.'),section('Further approach guidance',p.approach.slice(2),actions,'No further guidance from this record.'),section('Other next steps',p.next_steps.slice(1),actions,''));content.append(latest,topics,more);
      const policy=el('details',null,'workspace-panel recorded-policy');policy.append(el('summary','Recorded approach & evidence limits'));policy.append(el('p',`${p.policy.agent} · ${p.policy.author || 'Unknown author'} · source ${p.policy.commit || 'unrecorded'}`),el('p',p.policy.text),el('pre',JSON.stringify(p.policy.config,null,2)),evidence(p.policy,actions));p.limitations.forEach(t=>policy.append(el('p',t,'muted')));content.append(policy);
    }
    draw();return root;
  }
  function history(report,{api,alive,initial,remember}){
    const root=el('div',null,'history-browser'),sidebar=el('section',null,'history-sidebar'),viewer=el('section',null,'history-reader');
    const search=el('input');search.type='search';search.placeholder='Search cases, agents or outcomes…';search.setAttribute('aria-label','Search supplier history');
    const filter=el('select');filter.setAttribute('aria-label','Filter history outcome');[['','All outcomes'],['valid','Valid deals'],['other','Other supplier selected'],['review','Needs review']].forEach(([v,t])=>{const o=el('option',t);o.value=v;filter.append(o);});
    const count=el('p',null,'table-note'),list=el('div',null,'history-list');sidebar.append(el('h3','Conversation history'),search,filter,count,list);root.append(sidebar,viewer);
    let selected=initial?.negotiation_id || report.history[0]?.id, request=0;
    function draw(){const q=search.value.toLowerCase(),rows=report.history.filter(h=>`${h.case_id} ${h.agent} ${h.author} ${h.run_name} ${h.outcome.label} ${h.dataset}`.toLowerCase().includes(q) && (!filter.value || (filter.value==='review'?['failed','interrupted','invalid','unknown'].includes(h.outcome.kind):h.outcome.kind===filter.value)));count.textContent=`${rows.length} of ${report.history.length} saved conversations`;list.replaceChildren();
      rows.forEach(h=>{const b=el('button',null,'history-item');b.dataset.session=h.id;b.setAttribute('aria-current',h.id===selected?'true':'false');b.append(el('span',h.outcome.label,'badge'),el('strong',h.case_id),el('span',`${h.agent} · ${h.author || 'Unknown author'}`),el('small',`${date(h.date)} · ${new Date(h.date).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})} · ${h.messages} messages`),el('small',`${h.run_name} · ${h.id.slice(-6)}`,'history-run'));if(report.partitions.length>1)b.append(el('small',h.dataset.startsWith('unknown:')?'Unregistered source':`Data ${h.dataset.slice(0,8)}`));b.title=`${h.run_name} · ${h.reference.session_id || h.id}`;b.onclick=()=>open(h);list.append(b);});
      if(!rows.length)list.append(el('p','No conversations match these filters.','notice'));
    }
    async function open(h,ref){const token=++request;selected=h.id;remember?.(ref || h.reference);draw();viewer.replaceChildren(el('p','Loading saved conversation…','notice'));
      try{const d=await api(`/api/workspace/suppliers/${encodeURIComponent(h.reference.supplier_key)}?negotiation=${encodeURIComponent(h.id)}`);if(token!==request || !alive() || !root.isConnected)return;
        viewer.replaceChildren();const title=el('div',null,'history-reader-heading');title.append(el('p',`${h.case_id} · ${h.agent} · ${date(h.date)}`,'eyebrow'),el('h3',h.run_name),el('span',h.outcome.label,'badge'));viewer.append(title);
        const digest=el('details',null,'history-digest');digest.open=true;digest.append(el('summary','Conversation at a glance'));h.summary.forEach(i=>digest.append(el('p',i.text)));viewer.append(digest,HarveyConversations.render(d,{messageIndex:ref?.message_index}));
      }catch(e){if(token===request && alive())viewer.replaceChildren(el('p',e.message,'notice'));}}
    search.oninput=draw;filter.onchange=draw;draw();const first=report.history.find(h=>h.id===selected);if(first)queueMicrotask(()=>{if(alive() && root.isConnected)open(first,initial);});else viewer.append(el('p','No conversations in this evidence scope yet.','notice'));
    return root;
  }
  return {render,history};
})();

globalThis.HarveyConversations = (() => {
  const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!=null)n.textContent=String(text);if(cls)n.className=cls;return n;};
  const label=v=>String(v ?? 'Not recorded').replaceAll('_',' ');
  function value(k,v){if(v==null)return k==='index_clause'?'No index clause':'Not recorded';if(typeof v==='object')return JSON.stringify(v);return `${v}${k.endsWith('_days')?' days':k.endsWith('_months')?' months':k==='ppm_commitment'?' ppm':k==='unit_price'?' / recorded price unit':''}`;}
  function render(detail,{messageIndex=null}={}){
    const root=el('div',null,'conversation-reader'),toolbar=el('div',null,'conversation-toolbar'),search=el('input'),filter=el('select'),count=el('span',null,'muted small'),feed=el('div',null,'message-timeline');
    search.type='search';search.placeholder='Find in this conversation…';search.setAttribute('aria-label','Search conversation messages');filter.setAttribute('aria-label','Filter conversation messages');[['all','All messages'],['supplier','Supplier replies'],['buyer','Buyer messages'],['offers','With offers']].forEach(([v,t])=>{const o=el('option',t);o.value=v;filter.append(o);});
    const latest=el('button','Latest message ↓','button secondary');toolbar.append(search,filter,latest);root.append(toolbar,count);
    if(detail.evidence_truncated)root.append(el('p','The original upload was truncated; this view may be incomplete.','notice'));
    root.append(feed);const open=new Set(messageIndex!=null?[messageIndex]:[]);let expandedOffers=new Set();
    function draw(){
      feed.querySelectorAll('.message-body').forEach(d=>{if(d.open)open.add(Number(d.dataset.index));else open.delete(Number(d.dataset.index));});expandedOffers=new Set([...feed.querySelectorAll('.message-offers[open]')].map(d=>d.dataset.index));feed.replaceChildren();
      const q=search.value.trim().toLowerCase(),sheetsByRole={};let shown=0;
      detail.messages.forEach((m,i)=>{
        const buyer=m.from==='buyer',sheets=Array.isArray(m.term_sheets)?m.term_sheets.filter(s=>s?.terms && typeof s.terms==='object'):[],previous=sheetsByRole[buyer?'buyer':'supplier'];if(sheets.length)sheetsByRole[buyer?'buyer':'supplier']=sheets.at(-1).terms;
        if((filter.value==='buyer'&&!buyer)||(filter.value==='supplier'&&buyer)||(filter.value==='offers'&&!sheets.length)||!`${m.body || ''} ${m.subject || ''} ${JSON.stringify(m.term_sheets || [])} ${JSON.stringify(m.action || '')}`.toLowerCase().includes(q))return;shown++;
        const card=el('article',null,`message-card ${buyer?'buyer':'supplier'}${i===messageIndex?' cited-message':''}`);card.dataset.index=i;
        const header=el('header'),who=el('div',null,'message-who');who.append(el('span',buyer?'H':'S','message-avatar'),el('strong',buyer?'Harvey · buyer':m.from_name || 'Supplier'));header.append(who,el('span',`#${i+1}${m.timestamp?' · '+new Date(m.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}):''}`,'muted small'));card.append(header);
        if(m.subject)card.append(el('h4',m.subject));
        if(m.body){const d=el('details',null,'message-body');d.dataset.index=i;d.open=open.has(i);const preview=m.body.replace(/\s+/g,' ').trim();d.append(el('summary',preview.length>210?preview.slice(0,210)+'… · Read full message':preview),el('p',m.body));card.append(d);}
        if(m.action)card.append(el('span',`Buyer action: ${label(typeof m.action==='string'?m.action:m.action.type)}${m.action.term_sheet_id?' · '+m.action.term_sheet_id:''}`,'message-action'));
        if(sheets.length){const chips=el('div',null,'term-chips');for(const k of ['unit_price','payment_days','contract_months','lead_time_days','ppm_commitment']){const v=sheets.at(-1).terms[k];if(v!=null){const changed=previous && previous[k]!=null && JSON.stringify(previous[k])!==JSON.stringify(v);const chip=el('span',`${label(k)}: ${changed?value(k,previous[k])+' → ':''}${value(k,v)}`,changed?'term-chip changed':'term-chip');chips.append(chip);}}card.append(chips);
          const terms=el('details',null,'message-offers');terms.dataset.index=i;terms.open=expandedOffers.has(String(i));terms.append(el('summary',`${sheets.length} structured ${sheets.length===1?'offer':'offers'} · all terms`));sheets.forEach((sheet,j)=>{terms.append(el('p',sheet.term_sheet_id || `Offer ${j+1}`,'muted small'));const dl=el('dl',null,'field-list');Object.entries(sheet.terms).forEach(([k,v])=>dl.append(el('dt',label(k)),el('dd',value(k,v))));terms.append(dl);});card.append(terms);}
        if(m.status)card.append(el('span',`Recorded status: ${label(m.status)}`,'message-state'));
        if(Array.isArray(m.missing_fields)&&m.missing_fields.length)card.append(el('p',`Missing terms: ${m.missing_fields.map(label).join(', ')}`,'error'));
        feed.append(card);
      });
      count.textContent=`${shown} / ${detail.messages.length} messages · original order · changed terms highlighted`;
      if(!shown)feed.append(el('p',detail.messages.length?'No messages match the current filters.':'No messages were included in this saved snapshot.','notice'));
    }
    search.oninput=draw;filter.onchange=draw;latest.onclick=()=>feed.lastElementChild?.scrollIntoView({block:'nearest',behavior:'smooth'});draw();
    if(messageIndex!=null)queueMicrotask(()=>{if(root.isConnected)feed.querySelector(`[data-index="${messageIndex}"]`)?.scrollIntoView({block:'nearest'});});return root;
  }
  return {render};
})();
