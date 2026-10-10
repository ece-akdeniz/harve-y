"""Screening must stop on failed/unreconciled requests and retain unknown counts."""
import importlib.util
import json
import sys
from pathlib import Path

from negotiator.state import Journal

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('staged_batch', TOOLS / 'staged_batch.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_hosted_timeout_lists_and_claim_gate(tmp_path):
    class Client:
        def session(self, sid):
            return {'status': 'ended', 'threads': {'sup:X': {}}}

        def thread(self, sid, supplier):
            return {'timeouts': [], 'messages': [{'claim_results': [{'result': 'contradicted'}]}]}

    run = {'returncode': 0, 'timed_out': False,
           'cases': {'case:X': {'session': 's', 'score': 0.5, 'must_haves_ok': True}}}
    problems = module.inspect_run(Client(), run, tmp_path)
    assert run['cases']['case:X']['timeouts'] == 0
    assert any('contradicted' in p for p in problems)
    assert json.loads((tmp_path / 'server-evidence.json').read_text())


def test_unresolved_intent_stops_new_starts(tmp_path):
    journal = Journal(tmp_path / 'journal.jsonl')
    journal.intent('case:X', 's', 'sup:X', 'send', {'message': {}})
    run = {'returncode': 1, 'timed_out': False, 'cases': {}}
    problems = module.inspect_run(None, run, tmp_path)
    assert 'unreconciled requests' in problems
    assert 'runtime failure or missing result' in problems
