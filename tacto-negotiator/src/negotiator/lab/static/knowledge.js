"use strict";
// Supplied evidence is rendered as text. Conceptual feeds never initiate requests.
globalThis.HarveyKnowledge = (() => {
  const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!=null)n.textContent=String(text);if(cls)n.className=cls;return n;};
  const pretty=value=>String(value ?? 'Unknown').replaceAll('_',' ');
  const date=value=>value ? new Date(value).toLocaleString() : 'Not registered';
  let generation=0, current=null;
  function reset(){generation++;current=null;}
  function fields(values){const dl=el('dl',null,'field-list');for(const [k,v] of Object.entries(values || {}))dl.append(el('dt',pretty(k)),el('dd',typeof v==='object'?JSON.stringify(v):pretty(v)));return dl;}
  function select(label,options,value,change){const wrap=el('label',label),s=el('select');s.setAttribute('aria-label',label);for(const [id,name] of options){const o=el('option',name);o.value=id;s.append(o);}s.value=value;s.onchange=()=>change(s.value);wrap.append(s);return wrap;}
  function sourceConcept(g){
    const box=el('section',null,'workspace-panel source-concept');box.append(el('p','DATA SOURCES','eyebrow'),el('h3','Fresh evidence, with a traceable source.'));
    const flow=el('div',null,'ingestion-flow');
    for(const [i,[title,copy]] of [['Supplied datasets','Active · versioned test / release files'],['Source checks','Dates, provenance & conflicting records'],['Shared graph','Supplier facts + saved agent observations']].entries()){
      const step=el('div',null,'ingestion-step');step.append(el('span',`0${i+1}`,'step-number'),el('strong',title),el('p',copy));flow.append(step);
    }
    box.append(flow);
    const meta=el('p',`Dataset checked ${date(g.freshness.checked_at)}. Latest dated supplier record: ${g.coverage.latest_source_date || 'Unknown'}. A recent ingestion does not mean the source itself is recent.`,'source-meta');box.append(meta);
    const preview=el('details',null,'external-concept');preview.append(el('summary','Explore future external sources · Concept only / not connected'));
    const branches=el('div',null,'concept-branches');
    for(const [title,copy] of [['News & company updates','Potential signals: capacity changes, ownership, supply disruptions.'],['Company identity matching','Match a real legal entity before attaching an external source.'],['Review & freshness checks','Keep publication dates, citations and conflicts before adding evidence.']]){const card=el('div');card.append(el('span','NOT CONNECTED','eyebrow'),el('strong',title),el('p',copy));branches.append(card);}
    preview.append(el('p','A proposed path into the shared graph: external sources → identity matching → source review → supplier evidence. Synthetic suppliers are never searched online.'),branches,el('p','This diagram is a product concept. It does not fetch news, schedule updates, or feed information to an agent.'));
    box.append(preview);return box;
  }
  function inspector(g,node,host,open){
    host.replaceChildren();host.append(el('p',pretty(node.kind),'eyebrow'),el('h3',node.label));
    if(node.status)host.append(el('span',node.status,'badge'));
    host.append(fields(node.values));
    const related=g.edges.filter(e=>e.source===node.id || e.target===node.id);
    const relations=el('details');relations.append(el('summary',`${related.length} graph connections`));
    related.slice(0,40).forEach(e=>{const other=g.nodes.find(n=>n.id===(e.source===node.id?e.target:e.source));const b=el('button',`${pretty(e.relation)} → ${other?.label || 'Unknown'}`,'relation-link');b.onclick=()=>inspector(g,other,host,open);relations.append(b);});
    if(related.length>40)relations.append(el('p','Showing the first 40 connections.'));
    host.append(relations,el('h4',`Source evidence · ${node.evidence.length} shown`));
    if(!node.evidence.length)host.append(el('p','This is a grouping node. Open its connections to inspect source evidence.'));
    node.evidence.forEach((e,i)=>{const d=el('details');d.append(el('summary',`${i+1}. ${e.source_id || e.case_id || 'Recorded source'}${e.message_index!=null?` · message ${e.message_index+1}`:''}`),fields(e));const h=g.report?.history.find(h=>h.reference.session_id===e.session_id && h.arena===e.arena && h.dataset===e.dataset);if(h && open){const b=el('button','Open original conversation ↗','text-button');b.onclick=()=>open({...h.reference,message_index:e.message_index});d.append(b);}host.append(d);});
    if(node.values.support_count>node.evidence.length)host.append(el('p',`${node.values.support_count} supporting observations in total; up to 20 citations shown.`));
  }
  function renderGraph(s,g){
    const root=s.body;root.replaceChildren();s.graph=g;
    const heading=el('div',null,'knowledge-heading');heading.append(el('div',null));heading.firstChild.append(el('h2',g.name));
    heading.append(el('span',g.dataset==='history'?'All saved history':'Supplied data + saved conversations','scope-label'));heading.title=`Supplier ${g.supplier} · data ${g.dataset}`;root.append(heading);
    const metrics=el('div',null,'knowledge-metrics');for(const [value,label] of [[g.coverage.source_facts,'source records'],[g.coverage.sessions,'saved negotiations'],[g.coverage.contributors,'agent configurations'],[g.coverage.shared_observations,'shared observations']]){const m=el('div');m.append(el('strong',value),el('span',label));metrics.append(m);}
    if(g.dataset!=='history' && g.coverage.all_historical_sessions>g.coverage.sessions){const note=el('details',null,'scope-note');note.append(el('summary',`${g.coverage.all_historical_sessions-g.coverage.sessions} more conversations in other data versions`),el('p','Use Data filters → Run history across versions to review them separately.'));root.append(note);}
    const sections={brief:el('div'),graph:el('div'),history:el('div'),sources:el('div')},nav=el('nav',null,'knowledge-tabs');nav.setAttribute('aria-label','Shared knowledge sections');
    const viewButtons={};
    function alive(){return current===s && root.contains(sections.history) && root.isConnected;}
    function open(ref){s.selectedReference=ref;sections.history.replaceChildren(HarveyBrief.history(g.report,{api:s.api,alive,initial:ref,remember:r=>{s.selectedReference=r;}}));showView('history');}
    const actions={get partition(){return s.partition;},set partition(value){s.partition=value;},open,inspect:id=>{const node=g.nodes.find(n=>n.id===id);if(node){s.node=id;inspector(g,node,s.inspector,open);showView('graph');s.inspector.scrollIntoView({block:'nearest'});}}};
    function showView(view){s.view=view;Object.entries(sections).forEach(([key,host])=>{host.hidden=key!==view;viewButtons[key].setAttribute('aria-current',key===view?'page':'false');});if(view==='history'&&!sections.history.childNodes.length)sections.history.append(HarveyBrief.history(g.report,{api:s.api,alive,initial:s.selectedReference,remember:r=>{s.selectedReference=r;}}));}
    for(const [key,name] of [['brief','Supplier brief'],['history','Conversations'],['graph','Knowledge graph'],['sources','Data sources']]){const b=el('button',name);b.dataset.knowledgeView=key;b.onclick=()=>showView(key);viewButtons[key]=b;nav.append(b);}
    root.append(nav,...Object.values(sections));sections.graph.append(metrics);sections.brief.append(HarveyBrief.render(g.report,actions));
    const layout=el('div',null,'knowledge-layout'),map=el('section',null,'graph-panel'),explorer=el('section',null,'graph-explorer');
    const mapHead=el('div',null,'section-heading');mapHead.append(el('h3','Supplier knowledge graph'),el('span',`${g.nodes.length} nodes · ${g.edges.length} connections`,'muted small'));map.append(mapHead,el('p','Grouped by evidence type. Choose a group to explore its records and sources.','muted small'));
    const canvas=el('div',null,'graph-canvas'),svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 600 440');svg.setAttribute('preserveAspectRatio','none');svg.setAttribute('aria-hidden','true');canvas.append(svg);
    const center=el('button',null,'graph-center');center.append(el('span','SUPPLIER'),el('strong',g.name),el('small',g.supplier));center.onclick=()=>inspector(g,g.nodes.find(n=>n.id===g.root),s.inspector,open);canvas.append(center);
    const positions=[[23,14],[77,14],[87,39],[87,67],[77,90],[23,90],[13,67],[13,39]];
    const activeGroups=g.groups.filter(v=>v.count);if(!activeGroups.some(v=>v.id===s.group))s.group=activeGroups.find(v=>v.id==='memory')?.id || activeGroups[0]?.id;
    const buttons=[];
    g.groups.forEach((group,i)=>{const [x,y]=positions[i];const line=document.createElementNS(svg.namespaceURI,'line');for(const [k,v] of Object.entries({x1:300,y1:220,x2:x*6,y2:y*4.4}))line.setAttribute(k,v);line.setAttribute('class',group.count?'':'empty-line');svg.append(line);
      const b=el('button',null,'graph-group');b.style.left=x+'%';b.style.top=y+'%';b.dataset.group=group.id;b.disabled=!group.count;b.setAttribute('aria-pressed',String(s.group===group.id));b.append(el('strong',group.count),el('span',group.label));b.onclick=()=>{s.group=group.id;s.limit=20;s.search='';search.value='';drawList();};buttons.push(b);canvas.append(b);
    });
    map.append(canvas,el('p','Facts, observations and unresolved conflicts remain distinct. Connections summarize saved evidence; they do not establish a stable supplier preference.','table-note'));
    const listTitle=el('h3'),search=el('input'),list=el('div',null,'graph-records'),more=el('button','Show more','button secondary');search.type='search';search.placeholder='Search this group…';search.setAttribute('aria-label','Search graph records');search.value=s.search;search.oninput=()=>{s.search=search.value;s.limit=20;drawList();};
    more.onclick=()=>{s.limit+=20;drawList();};explorer.append(listTitle,search,list,more);layout.append(map,explorer);sections.graph.append(layout);
    s.inspector=el('section',null,'workspace-panel evidence-inspector');s.inspector.setAttribute('aria-live','polite');sections.graph.append(s.inspector);
    function drawList(){
      const group=g.groups.find(v=>v.id===s.group);buttons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.group===s.group)));listTitle.textContent=group?.label || 'No evidence yet';
      const rows=g.nodes.filter(n=>n.group===s.group && `${n.label} ${JSON.stringify(n.values)}`.toLowerCase().includes(s.search.toLowerCase())).sort((a,b)=>String(b.values.date || '').localeCompare(String(a.values.date || '')));
      list.replaceChildren();rows.slice(0,s.limit).forEach(n=>{const b=el('button',null,'graph-record');b.append(el('strong',n.label),el('span',n.status || pretty(n.kind)));b.onclick=()=>{s.node=n.id;inspector(g,n,s.inspector,open);s.inspector.scrollIntoView({block:'nearest',behavior:'smooth'});};list.append(b);});more.hidden=rows.length<=s.limit;
      if(!rows.length)list.append(el('p','No matching records in this group.','notice'));
      listTitle.append(el('span',` ${rows.length}`,'muted small'));
    }
    drawList();const selected=g.nodes.find(n=>n.id===s.node) || g.nodes.find(n=>n.group===s.group) || g.nodes[0];inspector(g,selected,s.inspector,open);
    sections.sources.append(sourceConcept(g));sections.graph.append(el('p',g.boundary,'table-note'));showView(s.view || 'brief');
  }
  async function fetchGraph(s){
    const request=++s.request,token=generation;
    s.status.textContent='Loading source-backed graph…';
    const params=new URLSearchParams({environment:s.environment,supplier:s.supplier,dataset:s.dataset});if(s.arena)params.set('arena',s.arena);
    try{const data=await s.api(`/api/workspace/knowledge?${params}`);if(token!==generation || current!==s || request!==s.request)return;
      const signature=JSON.stringify({...data.graph,freshness:{...data.graph.freshness,as_of:null}});
      if(signature!==s.signature){renderGraph(s,data.graph);s.signature=signature;}
      s.status.textContent='';
    }catch(e){if(token===generation && current===s && request===s.request){s.status.textContent=e.message;s.body.replaceChildren(el('p','The selected evidence could not be loaded. Refresh to retry.','notice'));}}
  }
  async function load({host,api,environment,supplier=null,arena=null,force=false}){
    const key=JSON.stringify([environment,supplier,arena]);
    if(current?.host===host && current.key===key){if(force || Date.now()-current.loaded>30000){current.loaded=Date.now();await fetchGraph(current);}return;}
    reset();const token=generation;host.replaceChildren(el('p','Loading supplied datasets…','notice'));
    try{const {catalog}=await api('/api/workspace/knowledge');if(token!==generation || !host.isConnected)return;
      const s={host,api,environment,arena,key,loaded:Date.now(),supplier:supplier || catalog.suppliers.find(p=>p.has_history && p.datasets.includes(catalog.datasets[0]?.id))?.id || catalog.suppliers.find(p=>p.has_history)?.id || catalog.suppliers[0]?.id,dataset:'latest',group:'memory',limit:20,search:'',request:0};current=s;
      host.replaceChildren();const controls=el('div',null,'knowledge-controls');s.status=el('p',null,'table-note');s.status.setAttribute('role','status');s.body=el('div');
      const options=[['latest','Latest supplied dataset'],...catalog.datasets.map(d=>[d.id,`${d.label} · ${d.id.slice(0,8)}`]),['history','Run history across versions']];
      function change(){s.signature='';s.body.replaceChildren();s.node=null;s.search='';s.limit=20;s.selectedReference=null;s.partition=null;fetchGraph(s);}
      const extra=el('details',null,'knowledge-filter-details');extra.append(el('summary','Data filters'));extra.append(select('Evidence scope',options,s.dataset,v=>{s.dataset=v;change();}));
      if(!supplier)controls.append(select('Supplier',catalog.suppliers.map(p=>[p.id,`${p.name} · ${p.id}`]),s.supplier,v=>{s.supplier=v;change();}));
      if(!arena && catalog.arenas.length>1)extra.append(select('Run source',[['','All arenas · kept separate'],...catalog.arenas.map(a=>[a,a])],'',v=>{s.arena=v || null;change();}));
      controls.append(extra);host.append(controls,s.status,s.body);
      if(!s.supplier){s.status.textContent='No supplied suppliers or saved negotiations yet. Register a supplied dataset to start.';return;}
      await fetchGraph(s);
    }catch(e){if(token===generation)host.replaceChildren(el('p',e.message,'notice'));}
  }
  return {load,reset};
})();
