const {test:nodeTest}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const domPath=process.env.LAB_UI_DOM_MODULE;
const test=(name,fn)=>nodeTest(name,{skip:!domPath},fn);
const parseHTML=html=>require(domPath).parseHTML(html);
const root=path.join(__dirname,'../src/negotiator/lab/static');
function page(api=async()=>({})) {
 const {document,window}=parseHTML(fs.readFileSync(path.join(root,'index.html'),'utf8'));
 const proto=Object.getPrototypeOf(document.getElementById('memory-supplier'));
 Object.defineProperty(proto,'value',{configurable:true,get(){return (this.querySelector('option[selected]')||this.querySelector('option'))?.value||'';},set(v){for(const o of this.querySelectorAll('option')){if(o.value===v)o.setAttribute('selected','');else o.removeAttribute('selected');}}});
 proto.add=function(o){this.append(o);};
 const state={loggedIn:true,memoryGeneration:0};
 const opened=[];
 const c=vm.createContext({document,window,state,api,openDetail:id=>opened.push(id),Intl});
 const file=path.join(root,'memory.js');if(fs.existsSync(file))vm.runInContext(fs.readFileSync(file,'utf8'),c);
 return {ui:c.MemoryDashboard||{},document,state,opened};
}
const observation=i=>({evidence_id:'e'+i,kind:'supplier_statement',field:'contract_months',direction:'higher',value:null,
 excerpt:'<img src=x onerror="alert(1)">',citation:{supplier:i%2?'sup:A':'sup:B',case_id:i%3?'case:one':'case:two',
 environment:i%4?'sandbox':'practice',arena_url:'https://arena.test',session_id:'session:'+i,run_id:'run:'+i,
 campaign_id:null,attempt_id:'attempt:'+i,message_index:i,message_sha256:'a'.repeat(64)}});
const graph=()=>({observations:Array.from({length:61},(_,i)=>observation(i)),lessons:[{lesson_id:'preference:contract_months:higher',field:'contract_months',direction:'higher',evidence_ids:['e1','e2','e3'],supporting_suppliers:['A','B','C'],supporting_cases:['one','two'],arena_url:'https://arena.test',environment:'sandbox'}],conflicts:[{field:'payment_days',evidence_ids:['e4'],arena_url:'https://arena.test',environment:'sandbox'}],coverage:{session_count:61,supplier_count:3,case_count:2}});
test('Memory navigation separates general lessons and supplier history, shows diverse support, conflict and candidate status',()=>{
 const {ui,document}=page();assert.equal(typeof ui.render,'function');
 ui.render(graph(),[]);
 assert.ok(document.getElementById('nav-memory'));assert.ok(document.querySelector('script[src="/memory.js"]'));
 assert.match(document.getElementById('memory-lessons').textContent,/3 suppliers.*2 cases/);
 assert.match(document.getElementById('memory-lessons').textContent,/Candidate.*held.out/i);
 assert.match(document.getElementById('memory-lessons').textContent,/Conflict.*payment days.*abstain/i);
 assert.match(document.getElementById('memory-observations').textContent,/supplier statement/i);
});
test('history pagination keeps more than 25 observations usable and filters by supplier case and environment',()=>{
 const {ui,document}=page();assert.equal(typeof ui.page,'function');
 assert.equal(ui.page(graph().observations,{},1).rows.length,25);
 assert.equal(ui.page(graph().observations,{},3).rows.length,11);
 const selected=ui.page(graph().observations,{supplier:'sup:A',case:'case:one',environment:'sandbox'},1);
 assert.ok(selected.rows.length>0);assert.ok(selected.rows.every(o=>o.citation.supplier==='sup:A'&&o.citation.case_id==='case:one'&&o.citation.environment==='sandbox'));
 ui.init();ui.render(graph(),[]);
 assert.equal(document.querySelectorAll('#memory-observations article').length,25);
 document.getElementById('memory-next').click();
 assert.match(document.getElementById('memory-range').textContent,/26.*50.*61/);
});
test('citations drill down as text with source links and hostile supplier excerpts never become markup',()=>{
 const {ui,document,opened}=page();assert.equal(typeof ui.render,'function');ui.render(graph(),[]);
 const first=document.querySelector('#memory-observations article');
 assert.equal(first.querySelectorAll('img,script').length,0);
 assert.match(first.textContent,/<img src=x/);assert.match(first.textContent,/session:0.*attempt:0.*message 0/);
 first.querySelector('button').click();assert.deepEqual(opened,['run:0']);
 document.querySelector('#memory-lessons details').open=true;
 assert.match(document.getElementById('memory-lessons').textContent,/e1/);
});
test('insufficient evidence shows honest empty state and frozen snapshot discovery cohorts',()=>{
 const {ui,document}=page();assert.equal(typeof ui.render,'function');
 ui.render({...graph(),lessons:[],conflicts:[]},[{snapshot_id:'immutable-id',lessons:[],source_cases:['discovery:one'],source_suppliers:['sup:A'],source_sessions:['s:one'],environment:'sandbox',arena_url:'https://arena.test'}]);
 assert.match(document.getElementById('memory-lessons').textContent,/Insufficient evidence.*three.*two/i);
 assert.match(document.getElementById('memory-snapshots').textContent,/immutable-id.*discovery:one.*sup:A.*s:one/s);
 assert.match(document.getElementById('memory-snapshots').textContent,/Abstains/);
});
test('anonymous reads are skipped and reset clears logout data and rejects delayed completion',async()=>{
 let release;const pending=new Promise(resolve=>release=resolve);let calls=0;
 const {ui,document,state}=page(async url=>{calls++;return url.endsWith('/memory')?pending:{'memory-snapshots':[]};});
 assert.equal(typeof ui.refresh,'function');
 state.loggedIn=false;await ui.refresh();assert.equal(calls,0);
 state.loggedIn=true;ui.render(graph(),[]);const refresh=ui.refresh();
 state.loggedIn=false;state.memoryGeneration++;ui.reset();
 release(graph());await refresh;
 assert.equal(document.getElementById('memory-observations').textContent,'');
 assert.equal(document.getElementById('memory-lessons').textContent,'');
 assert.equal(document.getElementById('memory-snapshots').textContent,'');
});
test('actual app memory navigation reads only when authenticated and logout clears all memory',async()=>{
 const {document,window}=parseHTML(fs.readFileSync(path.join(root,'index.html'),'utf8'));
 const proto=Object.getPrototypeOf(document.getElementById('memory-supplier'));
 Object.defineProperty(proto,'value',{configurable:true,get(){return (this.querySelector('option[selected]')||this.querySelector('option'))?.value||'';},set(v){for(const o of this.querySelectorAll('option')){if(o.value===v)o.setAttribute('selected','');else o.removeAttribute('selected');}}});
 proto.add=function(o){this.append(o);};
 for(const id of ['detail-dialog','loop-dialog']){const d=document.getElementById(id);d.close=()=>{d.open=false;};}
 const calls=[];let release;let late=false;
 const pending=new Promise(resolve=>release=resolve);
 const c=vm.createContext({document,window,Intl,AbortSignal,setInterval(){},fetch:async url=>{
  calls.push(url);return {ok:true,status:200,json:async()=>url==='/api/loop/memory'?(late?pending:graph()):{'memory-snapshots':[]}};
 }});
 vm.runInContext(fs.readFileSync(path.join(root,'memory.js'),'utf8'),c);
 vm.runInContext(fs.readFileSync(path.join(root,'app.js'),'utf8').replace(/refresh\(\);\s*$/,''),c);
 await c.MemoryDashboard.refresh();assert.equal(calls.length,0);
 vm.runInContext('showWorkspace()',c);
 document.getElementById('nav-memory').click();await new Promise(r=>setImmediate(r));
 assert.equal(document.getElementById('memory-view').hidden,false);
 assert.equal(document.getElementById('runs-view').hidden,true);
 assert.equal(document.getElementById('loop-view').hidden,true);
 assert.match(document.getElementById('memory-lessons').textContent,/3 suppliers/);
 assert.ok(calls.includes('/api/loop/memory-snapshots'));
 late=true;const refresh=c.MemoryDashboard.refresh();
 await vm.runInContext('logout()',c);release(graph());await refresh;
 assert.equal(document.getElementById('workspace').hidden,true);
 for(const id of ['memory-lessons','memory-observations','memory-snapshots'])assert.equal(document.getElementById(id).textContent,'');
 assert.equal(document.getElementById('memory-supplier').options.length,1);
});
