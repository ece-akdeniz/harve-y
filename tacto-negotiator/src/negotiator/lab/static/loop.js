"use strict";
// Read-only presentation. Every action copies a command for an authenticated local CLI.
globalThis.LoopDashboard = (() => {
  const quote = value => "'" + String(value).replaceAll("'", "'\\''") + "'";
  const points = value => typeof value === 'number' && Number.isFinite(value)
  ? `${value > 0 ? '+' : ''}${new Intl.NumberFormat(undefined,{maximumFractionDigits:2}).format(value)}` : 'Unknown';
  const restoreCommand = id => `uv run --locked negotiator lab restore ${quote(id)} --destination ${quote(`../restore-${id}`)}`;
  const diffCommand = (base, candidate) => base?.commit && candidate?.commit
  ? `git diff ${quote(base.commit)} ${quote(candidate.commit)}` : 'Checkpoint commit metadata unavailable';
  // Gate details use strings, numbers, timeout objects and case/repetition arrays.
  // Keep every nested evidence field readable without interpreting it as markup.
  function evidenceText(value) {
    if (value == null) return 'Unknown';
    if (Array.isArray(value)) return value.map(evidenceText).join('; ');
    if (typeof value === 'object') {
      return Object.entries(value).map(([key, detail]) =>
      `${key.replaceAll('_', ' ')}: ${evidenceText(detail)}`).join(' · ');
    }
    return String(value);
  }
  function campaignView(c) {
    const evaluation = c.completion?.evaluation || c.evaluation || {};
    const messages = {
      baseline_superseded: 'The baseline was superseded. Compare this candidate against the new recommendation in a new campaign.',
      insufficient_evidence: 'Evidence is incomplete or invalid. Inspect all attempts and evidence gaps before planning another comparison.',
      rejected: 'The candidate did not pass all promotion gates. Inspect the failed gates and record a finding.',
      awaiting_review: 'All gates passed. A teammate must review this learning candidate before the recommendation changes.',
      promoted: 'All promotion gates passed. The lab recommendation was updated.',
      running: 'Comparison is running on a teammate’s laptop. Pending and failed attempts remain visible.'
    };
    return {
      message:messages[c.status] || String(c.status || 'Unknown status'),gates:evaluation.gates || [],gaps:evaluation.evidence_gaps || [],evaluation
    };
  }
  const node = (tag,text,cls) => {
    const n=document.createElement(tag);
    if(text!=null)n.textContent=String(text);
    if(cls)n.className=cls;
    return n;
  };
  const timestamp = value => typeof value==='number' ? new Date(value*1000).toLocaleString() : 'Unknown';
  function table(head,rows) {
    const shell=node('div',null,'table-shell');
    const t=node('table');
    const h=node('tr');
    head.forEach(x=>h.append(node('th',x)));
    const thead=node('thead');
    thead.append(h);
    t.append(thead);
    const body=node('tbody');
    rows.forEach(row=>{
      const tr=node('tr');
      row.forEach(x=>tr.append(node('td',x??'Unknown')));
      body.append(tr);
    });
    t.append(body);
    shell.append(t);
    return shell;
  }
  function command(text) {
    const wrap=node('div',null,'loop-command');
    const code=node('code',text);
    const button=node('button','Copy command','button secondary');
    button.type='button';
    button.addEventListener('click',async()=>{
      try{
        await navigator.clipboard.writeText(text);
        button.textContent='Copied';
      } catch{
        button.textContent='Select and copy the command';
      }
    });
    wrap.append(code,button);
    return wrap;
  }
  const section = title => {
    const n=node('section',null,'panel loop-panel');
    n.append(node('h3',title));
    return n;
  };
  let signature='', revision=0, current=null, detailRevision=0;
  function reset(){
    revision++;
    detailRevision++;
    signature='';
    current=null;
    const dialog=document.getElementById('loop-dialog');
    if(dialog?.open)dialog.close();
    document.getElementById('loop-content')?.replaceChildren();
    document.getElementById('loop-detail')?.replaceChildren();
  }
  function renderOverview(data) {
    const root=document.getElementById('loop-content');
    root.replaceChildren();
    const campaignCount=document.getElementById('campaign-count');
    if(campaignCount)campaignCount.textContent=String((data.campaigns||[]).length);
    const campaigns=section('Recorded comparisons');
    if(!(data.campaigns||[]).length)campaigns.append(node('p','No campaigns yet. Read the recommendation, create and publish a candidate, then run a bounded comparison.'),command('uv run --locked negotiator lab campaign run --help'));
    for(const c of [...(data.campaigns||[])].sort((a,b)=>(b.created_at||0)-(a.created_at||0))){
      const card=section(c.campaign_id);
      const counts=c.attempt_counts||{};
      card.append(node('p',`${c.author} · ${c.status} · ${c.suite_id}`),node('p',`${counts.completed??'?'} of ${counts.total??'?'} attempts completed${counts.failed?` · ${counts.failed} failed or recovered`:''}`,'muted'),node('p',c.hypothesis),node('p',campaignView(c).message));
      const button=node('button','View attempts, scores and gates','button secondary');
      button.addEventListener('click',()=>openCampaign(c.campaign_id));
      card.append(button);
      campaigns.append(card);
    }
    root.append(campaigns);
    const recs=section('Current recommendations');
    if(!(data.recommended||[]).length){
      recs.append(node('p','No recommendation yet. Publish a checkpoint, register the suite and explicitly seed a baseline.'),command('uv run --locked negotiator lab checkpoint create --description "Initial baseline"'),command('uv run --locked negotiator lab suite create'));
    }
    for(const rec of data.recommended||[]){
      const card=section(rec.suite_id);
      const suite=(data.suites||[]).find(s=>s.suite_id===rec.suite_id);
      card.append(node('p',`Checkpoint ${rec.checkpoint_id} · generation ${rec.generation}`),node('p',`${suite?.environment||'Unknown environment'} · ${suite?.runner||'Unknown runner'} · ${suite?.max_sessions??'?'} sessions per comparison · ${timestamp(rec.updated_at)}`),command(restoreCommand(rec.checkpoint_id)));
      recs.append(card);
    }
    root.append(recs);
    const families=section('Exploration budgets');
    families.append(table(['Family','Reserved / ceiling','Practice reserved / allowance','Protected reserve'],(data.families||[]).map(f=>[f.family_id,`${f.reserved_sessions} / ${f.max_sessions}`,`${f.practice_reserved} / ${f.practice_allowance}`,f.reserve])));
    families.append(node('p','Reservations remain charged. Practice quota is separately checked at reservation and each start.','muted'));
    root.append(families);
    const findings=section('Findings');
    for(const f of data.findings||[]){
      const card=section(`${f.disposition} · ${f.author}`);
      for(const key of ['observation','hypothesis','change','next_test'])card.append(node('p',`${key.replaceAll('_',' ')}: ${f[key]}`));
      card.append(node('p',`Confidence ${f.confidence} · candidate ${f.candidate_id}`));
      for (const ref of f.evidence || []) {
        let evidenceCommand = `uv run --locked negotiator lab evidence show ${quote(ref.attempt_id)}`;
        if (ref.supplier != null) evidenceCommand += ` --supplier ${quote(ref.supplier)}`;
        if (ref.message_index != null) evidenceCommand += ` --message ${ref.message_index}`;
        card.append(command(evidenceCommand));
      }
      findings.append(card);
    }
    if(!(data.findings||[]).length)findings.append(node('p','No findings recorded.'));
    root.append(findings);
    const history=section('Recommendation history');
    const list=node('ol');
    for(const event of data.history||[])list.append(node('li',`${timestamp(event.recommendation?.updated_at)} · ${event.action} · ${event.previous_id??'initial'} → ${event.checkpoint_id} · ${event.suite_id} · generation ${event.recommendation?.generation}`));
    history.append(list);
    root.append(history);
  }
  function disclosure(title,body){
    const d=node('details');
    d.append(node('summary',title),body);
    return d;
  }
  function renderCampaign(c, base, candidate) {
    const root = document.getElementById('loop-detail');
    root.replaceChildren();
    document.getElementById('loop-title').textContent = c.campaign_id;
    const view = campaignView(c);
    root.append(node('p', view.message), node('p', c.hypothesis));

    root.append(disclosure('Promotion gates', table(
      ['Gate', 'Result', 'Reason'],
      view.gates.map(g => [g.id, g.passed ? 'Pass' : 'Fail', evidenceText(g.detail)])
    )));
    const gaps = node('ul');
    view.gaps.forEach(g => gaps.append(node('li', evidenceText(g))));
    if (!view.gaps.length) {
      gaps.append(node('li', 'No reported evidence gaps. Running campaigns have not been evaluated yet.'));
    }
    root.append(disclosure('Evidence gaps', gaps));
    root.append(disclosure('Per-case scores (0–100) and spread', table(
      ['Case', 'Baseline mean ± SD', 'Candidate mean ± SD', 'Gain (points)'],
      (view.evaluation.cases || []).map(r => [
        r.case_id,
        `${points(r.baseline?.mean)} ± ${points(r.baseline?.spread)}`,
        `${points(r.candidate?.mean)} ± ${points(r.candidate?.spread)}`,
        points(r.gain)
      ])
    )));
    root.append(disclosure('Repetition blocks (all planned outcomes)', table(
      ['Repeat', 'Baseline', 'Candidate', 'Gain (points)'],
      (view.evaluation.repeats || []).map(r => [
        r.repeat, points(r.baseline), points(r.candidate), points(r.gain)
      ])
    )));
    const attemptEvidence=disclosure(`Attempt evidence (${(c.attempts||[]).length})`, table(
      ['Attempt', 'Arm / case / repeat', 'Status', 'Score', 'Timeouts', 'Session'],
      (c.attempts || []).map(a => [
        a.attempt_id, `${a.arm} / ${a.case_id} / ${a.repeat}`, a.status,
        typeof a.score === 'number' ? points(a.score * 100) : 'Unknown',
        a.timeouts ?? 'Unknown', a.session_id ?? 'Unknown'
      ])
    ));
    attemptEvidence.open=true;
    root.append(attemptEvidence);
    for (const a of c.attempts || []) {
      root.append(command(`uv run --locked negotiator lab evidence show ${quote(a.attempt_id)}`));
    }

    const changes = section('Checkpoint and configuration changes');
    changes.append(
      node('p', `Baseline ${c.baseline_id}: ${base?.commit ?? 'unavailable'} · Candidate ${c.candidate_id}: ${candidate?.commit ?? 'unavailable'}`),
      command(diffCommand(base, candidate))
    );
    const keys = new Set([
      ...Object.keys(base?.config || {}), ...Object.keys(candidate?.config || {})
    ]);
    const configRows = [...keys]
      .filter(k => JSON.stringify(base?.config?.[k]) !== JSON.stringify(candidate?.config?.[k]))
      .map(k => [
        k, JSON.stringify(base?.config?.[k]) ?? 'Unknown',
        JSON.stringify(candidate?.config?.[k]) ?? 'Unknown'
      ]);
    changes.append(table(['Public config', 'Baseline', 'Candidate'], configRows));
    changes.append(node('p', 'Source bytes remain in Git. Run the diff locally after fetching published checkpoint refs.'));
    root.append(changes, command(restoreCommand(c.candidate_id)));
  }
  async function openCampaign(id,background=false){
    const request=++detailRevision;
    const auth=revision;
    const dialog=document.getElementById('loop-dialog');
    current=id;
    if(background&&!dialog.open)return;
    if(!background){
      document.getElementById('loop-title').textContent=id;
      document.getElementById('loop-detail').replaceChildren(node('p','Loading campaign evidence…'));
      if(!dialog.open)dialog.showModal();
    }
    try {
      const c=await api(`/api/loop/campaigns/${encodeURIComponent(id)}`);
      const manifests=await Promise.all([c.baseline_id,c.candidate_id].map(k=>api(`/api/loop/checkpoints/${encodeURIComponent(k)}`).catch(()=>null)));
      if(request!==detailRevision||auth!==revision||!dialog.open||current!==id)return;
      const opened=[...document.querySelectorAll("#loop-detail details")].map(n=>n.open);
      const scroll=dialog.scrollTop;
      renderCampaign(c,...manifests);
      if(background){
        document.querySelectorAll("#loop-detail details").forEach((n,i)=>{
          n.open=opened[i]||false;
        });
        dialog.scrollTop=scroll;
      }
    } catch(error){
      if(request===detailRevision&&auth===revision&&dialog.open)document.getElementById('loop-detail').replaceChildren(node('p',error.message,'error'));
    }
  }
  async function refresh(){
    const request=revision;
    try{
      const data=await api('/api/loop/overview');
      if(request!==revision||!state.loggedIn)return;
      document.getElementById('loop-error').textContent='';
      const next=JSON.stringify(data);
      if(signature!==next){
        renderOverview(data);
        signature=next;
      }
    if(current&&document.getElementById("loop-dialog").open)await openCampaign(current,true);
    } catch(error){
      if(request===revision&&state.loggedIn)document.getElementById('loop-error').textContent=`Could not refresh recommendation evidence. ${error.message}`;
    }
  }
  function init(){
    document.getElementById('loop-close').addEventListener('click',()=>document.getElementById('loop-dialog').close());
    document.getElementById('loop-dialog').addEventListener('close',()=>{
      current=null;
      detailRevision++;
    });
  }
  return {
    points,restoreCommand,diffCommand,campaignView,renderOverview,renderCampaign,refresh,reset,init,openCampaign
  };
})();
