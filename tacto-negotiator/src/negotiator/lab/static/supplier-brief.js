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
  function fold(title,...children){const d=el('details',null,'brief-fold');d.append(el('summary',title),...children);return d;}
  function short(text){return String(text).replaceAll('case:','').replaceAll(' per recorded price unit',' / price unit');}
  function render(report,actions){
    const root=el('div',null,'supplier-brief simple-brief');
    if(!report.partitions.length){root.append(el('h2','No conversations yet'),el('p','Review this supplier’s facts in the knowledge graph. Their history will appear here after a negotiation.'));return root;}
    let selected=report.partitions.find(p=>p.id===actions.partition)?.id || report.partitions[0].id;
    const content=el('div');
    if(report.partitions.length>1){
      const picker=el('select');picker.setAttribute('aria-label','Report evidence partition');
      report.partitions.forEach((p,i)=>{const o=el('option',`History ${i+1} · ${p.stats.sessions} negotiations · ${p.dataset.startsWith('unknown:')?'unregistered source':p.dataset.slice(0,8)}`);o.value=p.id;picker.append(o);});
      picker.value=selected;picker.onchange=()=>{selected=picker.value;draw();};
      root.append(fold('Choose a data version',el('p',report.boundary),picker));
    }
    root.append(content);
    function draw(){
      const p=report.partitions.find(p=>p.id===selected);actions.partition=selected;content.replaceChildren();
      const hero=el('section',null,'brief-hero');
      hero.append(el('h2','So far'),el('p',`${p.stats.sessions} negotiations · Latest: ${p.latest.outcome.label.toLowerCase()}`,'brief-lead'));
      const stats=el('div',null,'brief-stats');
      for(const [value,name] of [[p.stats.valid_deals,'confirmed deals'],[money(p.stats.latest_case_reduction_eur),'simulated savings']]){const x=el('div');x.append(el('strong',value),el('span',name));stats.append(x);}
      hero.append(stats);content.append(hero);
      const next=el('section',null,'next-priority');
      next.append(el('h2','Next time'),el('p',p.next_steps[0]?.status==='Review first'?'Review the flagged negotiation before trying again.':p.next_steps[0]?.status==='Untested suggestion'?'Try one permitted change. Compare the total cost before making a concession.':'Confirm the latest offer before negotiating.'));
      const actionsRow=el('div',null,'next-actions'),cta=el('button','Read latest conversation','button primary');cta.onclick=()=>actions.open(p.latest.reference);
      actionsRow.append(cta,el('span','Suggested · not yet tested','muted small'));next.append(actionsRow);content.append(next);
      const remember=el('section',null,'brief-remember');remember.append(el('h2','What to remember'));
      const facts=el('ul',null,'brief-points');
      if(p.memory[0]){const m=p.memory[0],context=m.title.startsWith('Observed offers')?short(m.title).replace('Observed offers ·','In')+': ':'';facts.append(el('li',context+short(m.text)));}
      if(p.approach[0])facts.append(el('li',short(p.approach[0].text)));
      if(!facts.childNodes.length)facts.append(el('li','There is not enough history to suggest an approach yet.'));
      remember.append(facts);content.append(remember);
      const latest=el('div',null,'latest-exchange');
      latest.append(el('h3','Latest conversation'));
      p.latest.summary.forEach(i=>{const row=el('div',null,'digest-beat');row.append(el('p',short(i.text)),evidence(i,actions));latest.append(row);});
      if(p.latest.truncated)latest.append(el('p','The saved conversation is incomplete.','notice'));
      const topics=el('div',null,'brief-topics');
      p.topics.forEach(t=>{const item=fold(`${t.title} · ${t.count} conversations`,el('p',t.text));t.evidence.forEach(ref=>item.append(el('blockquote',ref.quote),evidence({evidence:[ref]},actions)));topics.append(item);});
      const supporting=el('div',null,'brief-supporting');
      supporting.append(latest,section('Remembered facts',p.memory,actions,'No additional memory yet.'),section('Suggested approach',p.approach,actions,''),section('Next steps',p.next_steps,actions,''),fold('Conversation themes',topics));
      const policy=el('div');policy.append(el('p',p.policy.text),el('pre',JSON.stringify(p.policy.config,null,2)),evidence(p.policy,actions));
      supporting.append(fold('Saved agent settings',policy));
      content.append(fold('Read the full report & sources',supporting));
      const limits=el('div');limits.append(el('p',`${date(p.period.first)} – ${date(p.period.last)}. ${p.stats.messages} saved messages across ${p.stats.cases} cases. ${p.stats.other_selected} outcomes selected another supplier.`),el('p',`Savings cover ${p.stats.cost_coverage} latest cases. Repeated experiments are not added together. The opening baseline may be another RFQ supplier.`));p.limitations.forEach(t=>limits.append(el('p',t)));content.append(fold('About this summary',limits));
    }
    draw();return root;
  }
  function history(report,{api,alive,initial,remember}){
    const root=el('div',null,'history-browser'),sidebar=el('section',null,'history-sidebar'),viewer=el('section',null,'history-reader');
    const search=el('input');search.type='search';search.placeholder='Find a conversation…';search.setAttribute('aria-label','Search supplier history');
    const filter=el('select');filter.setAttribute('aria-label','Filter history outcome');[['','All outcomes'],['valid','Valid deals'],['other','Other supplier selected'],['review','Needs review']].forEach(([v,t])=>{const o=el('option',t);o.value=v;filter.append(o);});
    const count=el('p',null,'table-note'),list=el('div',null,'history-list');sidebar.append(el('h3','Conversations'),search,filter,count,list);root.append(sidebar,viewer);
    let selected=initial?.negotiation_id || report.history[0]?.id, request=0;
    function draw(){const q=search.value.toLowerCase(),rows=report.history.filter(h=>`${h.case_id} ${h.agent} ${h.author} ${h.run_name} ${h.outcome.label} ${h.dataset}`.toLowerCase().includes(q) && (!filter.value || (filter.value==='review'?['failed','interrupted','invalid','unknown'].includes(h.outcome.kind):h.outcome.kind===filter.value)));count.textContent=`${rows.length} of ${report.history.length} saved conversations`;list.replaceChildren();
      rows.forEach(h=>{const b=el('button',null,'history-item');b.dataset.session=h.id;b.setAttribute('aria-current',h.id===selected?'true':'false');b.append(el('strong',h.case_id.replace('case:','Case ')),el('span',h.outcome.label,'history-outcome'),el('small',`${date(h.date)} · ${new Date(h.date).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})} · ${h.id.slice(-4)}`));if(report.partitions.length>1)b.append(el('small',h.dataset.startsWith('unknown:')?'Unregistered source':`Data ${h.dataset.slice(0,8)}`));b.title=`${h.run_name} · ${h.agent} · ${h.author || 'Unknown author'} · ${h.reference.session_id || h.id}`;b.onclick=()=>open(h);list.append(b);});
      if(!rows.length)list.append(el('p','No conversations match these filters.','notice'));
    }
    async function open(h,ref){const token=++request;selected=h.id;remember?.(ref || h.reference);draw();viewer.replaceChildren(el('p','Loading saved conversation…','notice'));
      try{const d=await api(`/api/workspace/suppliers/${encodeURIComponent(h.reference.supplier_key)}?negotiation=${encodeURIComponent(h.id)}`);if(token!==request || !alive() || !root.isConnected)return;
        viewer.replaceChildren();const title=el('div',null,'history-reader-heading');title.append(el('h3',h.case_id.replace('case:','Case ')),el('span',`${h.outcome.label} · ${date(h.date)}`,'muted'));const info=el('details',null,'conversation-info');info.append(el('summary','Run details'),el('p',`${h.run_name} · ${h.agent} · ${h.author || 'Unknown author'}`));title.append(info);viewer.append(title,HarveyConversations.summary(h),HarveyConversations.render(d,{messageIndex:ref?.message_index}));
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
  function summary(digest){
    const box=el('section',null,'conversation-digest');box.append(el('h3','In brief'));
    const changes=(digest?.changes || []).slice(0,2);
    if(changes.length){const list=el('ul');changes.forEach(c=>list.append(el('li',c.text.replace(' per recorded price unit',' / price unit'))));box.append(list);}
    else box.append(el('p',digest?.outcome?.label || 'No recorded outcome yet.'));
    const full=el('details');full.append(el('summary','Opening offer & outcome'));(digest?.summary || []).forEach(i=>full.append(el('p',i.text)));box.append(full);return box;
  }
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
        const header=el('header'),who=el('div',null,'message-who');who.append(el('span',buyer?'H':'S','message-avatar'),el('strong',buyer?'Harvey':'Supplier'));header.append(who,el('span',`#${i+1}${m.timestamp?' · '+new Date(m.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}):''}`,'muted small'));card.append(header);
        if(m.subject)card.title=m.subject;
        if(m.body){const d=el('details',null,'message-body');d.dataset.index=i;d.open=open.has(i);const preview=m.body.replace(/\s+/g,' ').trim();d.append(el('summary',preview.length>140?preview.slice(0,140)+'…':preview),el('p',m.body));card.append(d);}
        if(m.action)card.append(el('span',`Buyer action: ${label(typeof m.action==='string'?m.action:m.action.type)}${m.action.term_sheet_id?' · '+m.action.term_sheet_id:''}`,'message-action'));
        if(sheets.length){const chips=el('div',null,'term-chips');for(const k of ['unit_price','payment_days','contract_months','lead_time_days','ppm_commitment']){const v=sheets.at(-1).terms[k];if(v!=null){const changed=previous && previous[k]!=null && JSON.stringify(previous[k])!==JSON.stringify(v);const chip=el('span',`${label(k)}: ${changed?value(k,previous[k])+' → ':''}${value(k,v)}`,changed?'term-chip changed':'term-chip');chips.append(chip);}}card.append(chips);
          const terms=el('details',null,'message-offers');terms.dataset.index=i;terms.open=expandedOffers.has(String(i));terms.append(el('summary',`${sheets.length} structured ${sheets.length===1?'offer':'offers'} · all terms`));sheets.forEach((sheet,j)=>{terms.append(el('p',sheet.term_sheet_id || `Offer ${j+1}`,'muted small'));const dl=el('dl',null,'field-list');Object.entries(sheet.terms).forEach(([k,v])=>dl.append(el('dt',label(k)),el('dd',value(k,v))));terms.append(dl);});card.append(terms);}
        if(m.status)card.title+=` · ${label(m.status)}`;
        if(Array.isArray(m.missing_fields)&&m.missing_fields.length)card.append(el('p',`Missing terms: ${m.missing_fields.map(label).join(', ')}`,'error'));
        feed.append(card);
      });
      count.textContent=`${shown} of ${detail.messages.length} messages`;
      if(!shown)feed.append(el('p',detail.messages.length?'No messages match the current filters.':'No messages were included in this saved snapshot.','notice'));
    }
    search.oninput=draw;filter.onchange=draw;latest.onclick=()=>feed.lastElementChild?.scrollIntoView({block:'nearest',behavior:'smooth'});draw();
    if(messageIndex!=null)queueMicrotask(()=>{if(root.isConnected)feed.querySelector(`[data-index="${messageIndex}"]`)?.scrollIntoView({block:'nearest'});});return root;
  }
  return {render,summary};
})();
