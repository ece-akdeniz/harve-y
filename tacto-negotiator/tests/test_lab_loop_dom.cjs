const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
// Optional: LAB_UI_DOM_MODULE=/absolute/path/to/linkedom node --test tests/test_lab_loop_dom.cjs
// Use an already-installed linkedom; no runtime dependency or automatic package fetch.
const test = require('node:test');
test('actual dashboard DOM smoke', {skip: !process.env.LAB_UI_DOM_MODULE && 'set LAB_UI_DOM_MODULE to installed linkedom'}, async () => {
const {parseHTML}=require(process.env.LAB_UI_DOM_MODULE);
const base=require('node:path').join(__dirname,'../src/negotiator/lab/static/');
const {document}=parseHTML(fs.readFileSync(base+'index.html','utf8'));
const ctx=vm.createContext({document,Intl,Date});vm.runInContext(fs.readFileSync(base+'loop.js','utf8'),ctx);
ctx.LoopDashboard.renderOverview({recommended:[{suite_id:'s',checkpoint_id:'cp',generation:2,updated_at:1790000000}],suites:[{suite_id:'s',environment:'sandbox',runner:'serial',max_sessions:12}],campaigns:[],families:[],findings:[],history:[{action:'seed',checkpoint_id:'cp',suite_id:'s',recommendation:{generation:2,updated_at:1790000000}}]});
assert.match(document.getElementById('loop-content').textContent,/generation 2/);assert.ok(document.getElementById('runs-view'));assert.ok(document.getElementById('compare-view'));assert.ok(document.getElementById('detail-dialog'));assert.equal(document.querySelector('script').getAttribute('src'),'/loop.js');assert.ok(document.getElementById('loop-dialog'));console.log('Actual index.html loop DOM smoke passed; existing views/dialog preserved.');
// Load the actual app with real DOM and fake read-only transport; no HTTP or hosted sessions.
const selectProto=Object.getPrototypeOf(document.getElementById('filter-author'));
selectProto.add=function(option){this.append(option);};
let routes=[];const transport=async path=>{routes.push(path);return {ok:true,status:200,json:async()=>path==='/api/runs'?{runs:[],team:'Smoke'}:{recommended:[],suites:[],campaigns:[],families:[],findings:[],history:[]}};};
ctx.fetch=transport;ctx.AbortSignal=AbortSignal;ctx.setInterval=()=>{};ctx.Option=function(text,value){const n=document.createElement('option');n.textContent=text;n.value=value;return n;};
for(const id of ['detail-dialog','loop-dialog']){const dialog=document.getElementById(id);dialog.showModal=()=>{dialog.open=true;};dialog.close=()=>{dialog.open=false;dialog.dispatchEvent(new document.defaultView.Event('close'));};}
vm.runInContext(fs.readFileSync(base+'app.js','utf8'),ctx);
await (async()=>{await vm.runInContext('state.refreshPromise',ctx);assert.equal(document.getElementById('workspace').hidden,false);assert.ok(routes.includes('/api/runs'));assert.ok(routes.includes('/api/loop/overview'));document.getElementById('nav-compare').click();assert.equal(document.getElementById('compare-view').hidden,false);document.getElementById('nav-runs').click();assert.equal(document.getElementById('runs-view').hidden,false);await vm.runInContext('logout()',ctx);assert.equal(document.getElementById('workspace').hidden,true);assert.equal(document.getElementById('loop-content').textContent,'');console.log('Actual index + app + loop integration passed: sign-in refresh, both GETs, compare/runs navigation, logout cleanup.');})();
});
