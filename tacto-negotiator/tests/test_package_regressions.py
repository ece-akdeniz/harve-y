"""Applicable checks from the earlier evidence branch.

Historical tests expecting non-standing acceptance are archived under experiments/.
Current hosted closing behavior is covered by test_evaluator.py and test_runner.py.
"""

import json
from pathlib import Path

from arena_kit.cost import must_haves_ok, total_cost

from negotiator.optimizer import best_terms, trade_packages
from negotiator.supplier_costs import estimated_cost


def case(name):
    return json.loads((Path(__file__).parent / "fixtures/package_cases.json").read_text())["cases"]["case:" + name]


def test_quality_tradeoffs_keep_fixed_payment_and_match_cost():
    c = case('P11')
    primary = best_terms(c, 43)
    assert primary['ppm_commitment'] == 1500
    packages = trade_packages(c, primary)
    assert len(packages) > 1
    assert any(p['chargeback_eur_per_complaint'] < 500 for p in packages)
    for p in packages:
        assert set(p) == set(c['negotiable'])
        assert 'payment_days' not in p
        assert must_haves_ok(c, p)
        assert total_cost(c, p) <= total_cost(c, primary) + 0.01


def test_relationship_estimate_is_scoped_to_supplier_and_part():
    c = case('P10')
    terms = {'unit_price': 30, 'volume_per_year': 23400, 'contract_months': 24, 'lead_time_days': 42}
    std = {'payment_days': 30, 'incoterm': 'DAP'}
    estimate = {'unit_cost': 29, 'confidence_pct': 5}
    plain = total_cost(c, terms, std)
    assert estimated_cost(c, 'sup:70410', terms, std, {('other', 'part:340010'): estimate}) == plain
    assert estimated_cost(c, 'sup:70410', terms, std, {('sup:70410', 'part:340010'): estimate}) > plain
