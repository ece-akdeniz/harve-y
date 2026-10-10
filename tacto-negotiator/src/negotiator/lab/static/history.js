"use strict";
globalThis.ScoreHistory = (() => {
  let points = [], revision = 0, busy = false, signature = null;
  const $ = id => document.getElementById(id);
  const valid = n => typeof n === 'number' && Number.isFinite(n);
  const format = n => valid(n) ? new Intl.NumberFormat(undefined, {maximumFractionDigits: 2}).format(n * 100) : '—';
  const change = n => valid(n) ? `${n > 0 ? '+' : ''}${format(n)}` : '—';
  const node = (tag, text, css) => {const n = document.createElement(tag); if(text != null)n.textContent=text;if(css)n.className=css;return n;};
  const day = time => {const d=new Date(time);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;};
  function model(input, filters = {}) {
    const groups = new Map();
    for(const p of input) {
      const date=day(p.started_at);
      if (!Number.isFinite(Date.parse(p.started_at)) || (filters.supplier && (p.supplier_id || '__none__')!==filters.supplier) ||
          (filters.case && p.case_id!==filters.case) || (filters.environment && p.environment!==filters.environment) ||
          (filters.from && date<filters.from) || (filters.to && date>filters.to)) continue;
      const key=JSON.stringify([p.arena_url,p.environment,p.case_id,p.supplier_id]);
      if(!groups.has(key))groups.set(key,{key,...p,points:[]});
      groups.get(key).points.push(p);
    }
    return [...groups.values()].map(g=>{
      g.points.sort((a,b)=>Date.parse(a.started_at)-Date.parse(b.started_at)||a.point_id.localeCompare(b.point_id,undefined,{numeric:true}));
      const scores=g.points.filter(p=>valid(p.score)).map(p=>p.score);
      return {...g,latest:scores.at(-1)??null,best:scores.length?Math.max(...scores):null,
        change:scores.length>1?scores.at(-1)-scores[0]:null,scored:scores.length};
    }).sort((a,b)=>a.environment.localeCompare(b.environment)||a.case_id.localeCompare(b.case_id,undefined,{numeric:true})||a.supplier_name.localeCompare(b.supplier_name));
  }
  const open = p => p.campaign_id ? globalThis.LoopDashboard?.openCampaign(p.campaign_id) : openDetail(p.run_id);
  const dateLabel = value => new Date(value).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
  function plot(group) {
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('viewBox','0 0 640 230');svg.setAttribute('class','history-chart');
    svg.setAttribute('role','group');svg.setAttribute('aria-label',`${group.supplier_name}, ${group.case_id}: score history from 0 to 100. Points open experiment details.`);
    const add=(tag,attrs,text)=>{const n=document.createElementNS(svg.namespaceURI,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(text!=null)n.textContent=text;svg.append(n);return n;};
    const times=group.points.map(p=>Date.parse(p.started_at)),min=Math.min(...times),max=Math.max(...times);
    const x=t=>min===max?330:48+(t-min)/(max-min)*560, y=s=>184-s*160;
    for(const s of [0,.5,1]) {add('line',{x1:48,x2:608,y1:y(s),y2:y(s),class:'chart-grid'});add('text',{x:36,y:y(s)+4,'text-anchor':'end',class:'chart-label'},s*100);}
    const segments=[];let current=[];
    for(const p of group.points) {
      if(!valid(p.score)||p.recovered){if(current.length)segments.push(current);current=[];continue;}
      current.push(`${x(Date.parse(p.started_at))},${y(p.score)}`);
    }
    if(current.length)segments.push(current);
    for(const segment of segments)add('polyline',{points:segment.join(' '),class:'chart-line'});
    for(const p of group.points.filter(p=>valid(p.score))) {
      const text=`${p.name}: ${format(p.score)} / 100 · ${dateLabel(p.started_at)} · ${p.recovered?'Recovered outcome · ':''}${p.source} · ${p.commit?p.commit.slice(0,7)+(p.dirty?' + changes':''):'Unknown version'}`;
      const circle=add('circle',{cx:x(Date.parse(p.started_at)),cy:y(p.score),r:5,class:p.recovered?'chart-point recovered':'chart-point',tabindex:0,role:'button','aria-label':text});
      const title=document.createElementNS(svg.namespaceURI,'title');title.textContent=text;circle.append(title);
      circle.addEventListener('click',()=>open(p));circle.addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();open(p);}});
    }
    add('text',{x:48,y:214,class:'chart-label'},dateLabel(group.points[0].started_at));
    add('text',{x:608,y:214,'text-anchor':'end',class:'chart-label'},dateLabel(group.points.at(-1).started_at));
    return svg;
  }
  function render() {
    const filters={supplier:$('history-supplier').value,case:$('history-case').value,environment:$('history-environment').value,from:$('history-from').value,to:$('history-to').value};
    const groups=model(points,filters),content=$('history-content');content.replaceChildren();
    $('history-count').textContent=`${groups.reduce((n,g)=>n+g.points.length,0)} attempts · ${groups.length} supplier/case series`;
    if(filters.from&&filters.to&&filters.from>filters.to){content.append(node('p','The end date must be on or after the start date.','notice'));return;}
    if(!groups.length){content.append(node('div',points.length?'No results match these filters.':'No recorded attempts yet. Run or import experiments to build the timeline.','empty-state panel'));return;}
    for(const g of groups) {
      const card=node('article',null,'panel history-card'),head=node('div',null,'history-card-heading');
      head.append(node('h3',g.supplier_name),node('span',`${g.case_id} · ${g.environment}`,'badge'));
      card.append(head,node('p',`${g.supplier_id || 'Outcome has no selected supplier'} · ${g.arena_url}`,'muted small'));
      const stats=node('div',null,'history-stats');
      for(const [label,value] of [['Latest scored',format(g.latest)],['Best',format(g.best)],['First → latest',change(g.change)],['Scored / attempts',`${g.scored} / ${g.points.length}`]]) {
        const stat=node('div');stat.append(node('span',label,'muted small'),node('strong',value));stats.append(stat);
      }
      card.append(stats,plot(g));
      const details=node('details',null,'history-attempts'),table=node('table'),tbody=node('tbody');
      details.append(node('summary',`Inspect ${g.points.length} attempts`));
      const thead=node('thead'),tr=node('tr');for(const label of ['WHEN','EXPERIMENT','SCORE','EVIDENCE','VERSION'])tr.append(node('th',label));thead.append(tr);table.append(thead,tbody);
      for(const p of g.points) {
        const row=node('tr'),when=node('td',dateLabel(p.started_at));when.title=`${p.time_basis} · ${p.started_at}`;
        const name=node('td'),button=node('button',p.name,'run-name');button.addEventListener('click',()=>open(p));name.append(button,node('span',`${p.author || 'Unknown owner'}${p.arm?' · '+p.arm:''}`,'subline'));
        row.append(when,name,node('td',valid(p.score)?format(p.score):'Not scored'),node('td',`${p.source} · ${p.status}${p.recovered?' · recovered outcome':''}`),node('td',p.commit?p.commit.slice(0,7)+(p.dirty?' + changes':''):'Unknown'));
        tbody.append(row);
      }
      const shell=node('div',null,'table-shell');shell.append(table);details.append(shell);card.append(details);content.append(card);
    }
  }
  function options(id,entries,placeholder) {
    const select=$(id),prior=select.value;
    select.replaceChildren();const add=(value,label)=>{const o=node('option',label);o.value=value;select.append(o);};add('',placeholder);
    for(const [value,label] of entries)add(value,label);
    select.value=entries.some(([value])=>value===prior)?prior:'';
  }
  function setPoints(input) {
    points=input;
    const suppliers=new Map(points.map(p=>[p.supplier_id||'__none__',p.supplier_id?`${p.supplier_name} · ${p.supplier_id}`:'No selected supplier']));
    options('history-supplier',[...suppliers].sort((a,b)=>a[1].localeCompare(b[1])),'All suppliers');
    options('history-case',[...new Set(points.map(p=>p.case_id))].sort().map(x=>[x,x]),'All cases');
    options('history-environment',[...new Set(points.map(p=>p.environment))].sort().map(x=>[x,x]),'All environments');
    render();
  }
  async function refresh() {
    if(busy || !state.loggedIn || $('history-view').hidden)return;
    busy=true;const request=revision;
    try {
      const body=await api('/api/score-history');
      if(request!==revision||!state.loggedIn)return;
      const next=JSON.stringify(body.points||[]);
      if(next!==signature){signature=next;setPoints(body.points||[]);}
      $('history-error').textContent='';
    } catch(error) {if(request===revision&&state.loggedIn)$('history-error').textContent=`History unavailable. ${error.message}`;}
    finally {if(request===revision)busy=false;}
  }
  function reset() {
    revision++;busy=false;signature=null;points=[];
    $('history-content').replaceChildren();$('history-count').textContent='';$('history-error').textContent='';
    options('history-supplier',[],'All suppliers');options('history-case',[],'All cases');options('history-environment',[],'All environments');
    $('history-from').value='';$('history-to').value='';
  }
  function init() {
    for(const id of ['history-supplier','history-case','history-environment','history-from','history-to'])$(id).addEventListener('change',render);
    $('history-clear').addEventListener('click',()=>{for(const id of ['history-supplier','history-case','history-environment','history-from','history-to'])$(id).value='';render();});
  }
  return {model,render,setPoints,refresh,reset,init};
})();
