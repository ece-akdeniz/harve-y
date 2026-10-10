from test_lab_server import snapshot

from negotiator.lab import score_history as module
from negotiator.lab.models import Run


def test_timeline_keeps_zero_missing_recovered_and_selected_supplier_distinct():
    bodies=[]
    for name,score,status in [('zero',0,'completed'),('good',.8,'completed'),('failed',None,'failed')]:
        b=snapshot(name,score=score,status=status)
        b['attempts'][0]['session_id']=name
        b['attempts'][0]['threads']={'sup:A':{'messages':[
            {'from':'buyer','from_name':'Buyer'}, {'from':'sales','from_name':'Supplier A'}]},'sup:B':{}}
        if name=='good':
            b['attempts'][0]['result']={'ended':True,'supplier_id':'sup:A'}
        if name=='failed':
            b['attempts'][0]['result']={'reconciled_result':{'score':.7,'supplier_id':'sup:B'}}
        bodies.append(Run.model_validate(b))
    assert hasattr(module,'score_history')
    points=module.score_history(bodies)['points']
    by_id={p['run_id']:p for p in points}
    assert by_id['zero']['score']==0
    assert by_id['zero']['supplier_id'] is None
    assert by_id['good']['supplier_id']=='sup:A'
    assert by_id['good']['supplier_name']=='Supplier A'
    assert by_id['failed']['recovered'] is True
    assert by_id['failed']['status']=='failed'
    assert by_id['failed']['score']==.7
    assert 'threads' not in by_id['good']
    assert by_id['good']['time_basis']=='Run start'


def test_campaign_session_deduplicates_import_and_uses_attempt_time():
    imported=snapshot('import-one',score=.8,status='completed')
    imported.update(source='imported',provenance=None)
    imported['attempts'][0].update(session_id='same-session',result={'supplier_id':'sup:A'})
    campaign={'campaign_id':'comparison','suite_id':'suite','created_at':1791633600,'author':'Baris','attempts':[
        {'attempt_id':'cell','case_id':'case:D01','checkpoint_id':'cp','arm':'candidate','status':'completed',
         'start':{'started_at':1791633660},'outcome':{'status':'completed','score':.8,'session_id':'same-session','result':{'ended':True,'supplier_id':'sup:A'},'threads':{}}}]}
    assert hasattr(module,'score_history')
    points=module.score_history([Run.model_validate(imported)],campaigns=[campaign],suites=[{'suite_id':'suite','environment':'sandbox','arena_url':'https://arena.tacto.ai'}],checkpoints=[{'checkpoint_id':'cp','commit':'abc'}])['points']
    assert len(points)==1
    assert points[0]['campaign_id']=='comparison'
    assert points[0]['commit']=='abc'
    assert points[0]['started_at']=='2026-10-10T12:01:00+00:00'
    assert points[0]['time_basis']=='Attempt start'
    assert points[0]['score']==.8


def test_campaign_recovery_uses_validated_top_level_score_and_preserves_original_status():
    from negotiator.lab.loop_models import Outcome, Reconciliation

    recovered = Outcome.model_validate(dict(attempt_id='cell', checkpoint_id='cp', session_id='session',
        status='recovered', score=.7, result={'ended': True, 'supplier_id': 'sup:A'})).model_dump()
    reconciliation = Reconciliation.model_validate(dict(attempt_id='cell', checkpoint_id='cp', session_id='session',
        score=.6, result={'ended': True, 'supplier_id': 'sup:B'},
        threads={'sup:B': {'messages': [{'from': 'sales', 'from_name': 'Recovered supplier'}]}})).model_dump()
    for status, outcome, recovery, expected in [
        ('recovered', recovered, None, .7),
        ('failed', {}, reconciliation, .6),
        ('completed', {**recovered, 'status': 'completed', 'result': {}}, reconciliation, .6),
    ]:
        attempt = dict(attempt_id='cell', case_id='D01', checkpoint_id='cp', arm='candidate',
            status=status, outcome=outcome, start={'started_at': 1791633660})
        if recovery:
            attempt['reconciliation'] = recovery
        campaign = dict(campaign_id='campaign', suite_id='suite', author='Tester',
            created_at=1791633600, attempts=[attempt])
        point = module.score_history([], campaigns=[campaign], suites=[dict(suite_id='suite',
            environment='sandbox', arena_url='https://arena.test')])['points'][0]
        assert point['score'] == expected
        assert point['recovered'] is True
        assert point['status'] == status
        assert point['session_id'] == 'session'
        if recovery:
            assert point['supplier_name'] == 'Recovered supplier'
