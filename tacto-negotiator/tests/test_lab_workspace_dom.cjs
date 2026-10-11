const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const domPath=process.env.LAB_UI_DOM_MODULE;
const base=path.join(__dirname,'../src/negotiator/lab/static/');

async function page() {
  const {parseHTML}=require(domPath),{document}=parseHTML(fs.readFileSync(base+'workspace.html','utf8'));
  const proto=Object.getPrototypeOf(document.getElementById('environment'));
  Object.defineProperty(proto,'value',{configurable:true,get(){return (this.querySelector('option[selected]')||this.querySelector('option'))?.value||'';},set(v){for(const o of this.querySelectorAll('option')){if(o.value===v)o.setAttribute('selected','');else o.removeAttribute('selected');}}});
  const data={summary:{savings_eur:120,savings_covered:1,savings_cases:2,savings_pct:12,suppliers:3,sessions:4,running:1},savings_basis:'Latest valid result per case.' ,suppliers:[
    {key:'late',name:'Late supplier',negotiations:[{id:'late-1',case_id:'P01',status:'running',stale:true,must_haves_ok:null,timeouts:0,updated_at:'2026-10-11T08:00:00Z'}]},
    {key:'timeout',name:'Timeout supplier',negotiations:[{id:'timeout-1',case_id:'P02',status:'completed',stale:false,must_haves_ok:true,timeouts:2,updated_at:'2026-10-11T09:00:00Z'}]},
    {key:'good',name:'Completed supplier',negotiations:[{id:'good-1',case_id:'P03',status:'completed',stale:false,must_haves_ok:true,timeouts:0,updated_at:'2026-10-11T10:00:00Z'}]},
  ]};
  const ctx=vm.createContext({document,Intl,Date,AbortSignal,setInterval(){},HarveyKnowledge:{reset(){},load:async()=>{}},HarveyConversations:{render:()=>document.createElement('div')},fetch:async route=>({ok:true,status:200,json:async()=>String(route).startsWith('/api/workspace')?data:{}})});
  vm.runInContext(fs.readFileSync(base+'workspace.js','utf8'),ctx);
  await new Promise(r=>setImmediate(r));
  return {ctx,document};
}

test('workspace overview ranks review work and keeps it out of learnings',{skip:!domPath},async()=>{
  const {document:d}=await page();
  const review=[...d.querySelectorAll('#attention .activity-row')];
  assert.deepEqual(review.map(row=>row.querySelector('strong').textContent),['Late supplier','Timeout supplier']);
  assert.match(d.getElementById('decision-brief').textContent,/Late supplier/);
  assert.equal(d.getElementById('operational-strip').textContent.includes('Needs review'),true);
  const learning=[...d.querySelectorAll('#activity .activity-row')];
  assert.deepEqual(learning.map(row=>row.querySelector('strong').textContent),['Completed supplier']);
  assert.equal(learning[0].getAttribute('href'),'#supplier/good/good-1');
});
