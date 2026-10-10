const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function ui(extra={}) {const c=vm.createContext({Intl,Date,...extra});const file=path.join(__dirname,'../src/negotiator/lab/static/history.js');if(fs.existsSync(file))vm.runInContext(fs.readFileSync(file,'utf8'),c);return {c,ui:c.ScoreHistory||{}};}
const point=(id,score,extra={})=>({point_id:id,name:id,run_id:id,source:'tracked',status:score==null?'failed':'completed',score,started_at:'2026-10-10T12:00:00Z',supplier_id:'A',supplier_name:'Supplier A',case_id:'D01',environment:'sandbox',arena_url:'https://arena.test',...extra});
test('history separates case, supplier, environment and arena, preserving zeros and missing outcomes',()=>{
 const {ui:history}=ui();assert.equal(typeof history.model,'function');
 const groups=history.model([point('zero',0),point('next',.8,{started_at:'2026-10-11T12:00:00Z'}),point('failed',null,{started_at:'2026-10-12T12:00:00Z'}),point('othercase',.7,{case_id:'D02'}),point('practice',.6,{environment:'practice'}),point('otherarena',.4,{arena_url:'https://other.test'}),point('none',0,{supplier_id:null,supplier_name:'No selected supplier'})],{});
 assert.equal(groups.length,5);
 const g=groups.find(g=>g.points.some(p=>p.point_id==='zero'));
 assert.equal(g.latest,.8);assert.equal(g.best,.8);assert.equal(g.change,.8);assert.equal(g.scored,2);assert.equal(g.points.length,3);
});
test('history dates and supplier filters apply before computing first-to-latest change',()=>{
 const {ui:history}=ui();assert.equal(typeof history.model,'function');
 const groups=history.model([point('old',.1,{started_at:'2026-10-09T12:00:00Z'}),point('a',.8),point('b',.7,{started_at:'2026-10-10T13:00:00Z'}),point('other',1,{supplier_id:'B'})],{from:'2026-10-10',to:'2026-10-10',supplier:'A'});
 assert.equal(groups.length,1);assert.equal(groups[0].points.length,2);assert.ok(Math.abs(groups[0].change+.1)<1e-9);
});
test('tracked repetitions with the same run timestamp retain numeric execution order',()=>{
 const {ui:history}=ui();const points=Array.from({length:12},(_,i)=>point('run:D01:'+(i+1),(i+1)/20));
 const g=history.model(points,{})[0];assert.equal(g.latest,.6);assert.ok(Math.abs(g.change-.55)<1e-9);
 assert.equal(g.points[1].point_id,'run:D01:2');assert.equal(g.points.at(-1).point_id,'run:D01:12');
});
