const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const domPath=process.env.LAB_UI_DOM_MODULE;
const base=path.join(__dirname,'../src/negotiator/lab/static/');
async function page() {
 const {parseHTML}=require(domPath),{document}=parseHTML(fs.readFileSync(base+'index.html','utf8'));
 const proto=Object.getPrototypeOf(document.getElementById('filter-author'));
 // linkedom lacks browser select.value setters and select.add.
 Object.defineProperty(proto,'value',{configurable:true,get(){return (this.querySelector('option[selected]')||this.querySelector('option'))?.value||'';},set(v){for(const o of this.querySelectorAll('option')){if(o.value===v)o.setAttribute('selected','');else o.removeAttribute('selected');}}});
 proto.add=function(o){this.append(o);};
 for(const id of ['detail-dialog','loop-dialog']){const d=document.getElementById(id);d.showModal=()=>{d.open=true;};d.close=()=>{d.open=false;d.dispatchEvent(new document.defaultView.Event('close'));};}
 const rows=Array.from({length:60},(_,i)=>({run_id:'r'+i,name:'Test '+i,author:i%2?'Baris':'Other',environment:'sandbox',status:'completed',updated_at:`2026-10-10T12:00:${String(i).padStart(2,'0')}Z`,metrics:{mean_score:i/100,completed:1,planned:1}}));
 const points=[{point_id:'p',run_id:'r59',name:'Test 59',author:'Baris',supplier_name:'<img src=x onerror=bad()>',supplier_id:'A',case_id:'D01',environment:'sandbox',arena_url:'https://arena.test',score:.59,status:'completed',source:'tracked',started_at:'2026-10-10T12:00:59Z',time_basis:'Run start',commit:'abc1234',dirty:true}];
 let historyResponse=null;
 const ctx=vm.createContext({document,Intl,Date,URL,AbortSignal,setInterval(){},Option:function(t,v){const o=document.createElement('option');o.textContent=t;o.value=v;return o;},fetch:async route=>({ok:true,status:200,json:async()=>route==='/api/runs'?{runs:rows}:route==='/api/score-history'?(historyResponse?await historyResponse:{points}):{recommended:[],suites:[],campaigns:[],families:[],findings:[],history:[]}})});
 for(const file of ['loop.js','history.js','app.js'])vm.runInContext(fs.readFileSync(base+file,'utf8'),ctx);
 await vm.runInContext('state.refreshPromise',ctx);
 return {ctx,document,rows,points,delayHistory(p){historyResponse=p;},event(id,type){document.getElementById(id).dispatchEvent(new document.defaultView.Event(type));}};
}
test('actual experiments table pages, sorts all rows, resets filters and preserves page on refresh',{skip:!domPath},async()=>{
 const {document:d,ctx,event}=await page();
 const names=()=>[...d.querySelectorAll('#runs-body .run-name')].map(n=>n.textContent);
 assert.equal(names().length,25);assert.equal(names()[0],'Test 59');
 d.getElementById('page-next').click();assert.equal(names()[0],'Test 34');
 d.getElementById('sort-name').click();assert.equal(names()[0],'Test 0');assert.equal(d.getElementById('sort-name').parentElement.getAttribute('aria-sort'),'ascending');
 d.getElementById('page-next').click();assert.equal(names()[0],'Test 25');
 await vm.runInContext('refresh()',ctx);assert.equal(names()[0],'Test 25');
 d.getElementById('search').value='Test 59';event('search','input');assert.deepEqual(names(),['Test 59']);assert.equal(d.getElementById('page-prev').disabled,true);
 d.getElementById('search').value='';event('search','input');d.getElementById('page-size').value='50';event('page-size','change');assert.equal(names().length,50);
 d.getElementById('sort-score').click();assert.equal(names()[0],'Test 59');d.getElementById('sort-score').click();assert.equal(names()[0],'Test 0');
});
test('actual history escapes names, opens points, renders campaign links, and discards late logout responses',{skip:!domPath},async()=>{
 const {document:d,ctx,points,delayHistory}=await page();
 d.getElementById('nav-history').click();await new Promise(r=>setImmediate(r));
 assert.equal(d.getElementById('history-view').hidden,false);assert.equal(d.querySelectorAll('.history-card').length,1);
 assert.equal(d.querySelectorAll('#history-content img').length,0);assert.match(d.getElementById('history-content').textContent,/<img src=x/);
 let opened=null;ctx.openDetail=id=>{opened=id;};d.querySelector('.chart-point').dispatchEvent(new d.defaultView.Event('click'));assert.equal(opened,'r59');
 let campaign=null;ctx.LoopDashboard.openCampaign=id=>{campaign=id;};ctx.ScoreHistory.setPoints([{...points[0],campaign_id:'campaign-one',run_id:null}]);d.querySelector('.chart-point').dispatchEvent(new d.defaultView.Event('click'));assert.equal(campaign,'campaign-one');
 d.getElementById('history-from').value='2026-10-10';
 let release;delayHistory(new Promise(r=>{release=r;}));const pending=ctx.ScoreHistory.refresh();vm.runInContext('showLogin()',ctx);release({points});await pending;
 assert.equal(d.getElementById('history-content').children.length,0);
 assert.equal(d.getElementById('history-supplier').options.length,1);assert.equal(d.getElementById('history-case').options.length,1);assert.equal(d.getElementById('history-from').value,'');
 assert.equal(d.getElementById('workspace').hidden,true);
});
