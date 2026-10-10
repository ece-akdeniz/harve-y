"""Internal should-cost estimates; never presented as supplier-known economics."""

from arena_kit.cost import total_cost


def load_estimates(package):
    if package.db is None:
        return {}
    rows = package.query(
        'SELECT s.* FROM should_cost s JOIN parts p ON p.id = s.part_id '
        'WHERE s.price_unit = p.price_unit', limit=10000
    )
    return {(r['supplier_id'], r['part_id']): r for r in rows
            if r.get('unit_cost', 0) > 0 and 0 <= r.get('confidence_pct', -1) <= 100}


def estimated_cost(case, supplier_id, terms, standard, estimates):
    if case['buyer'].get('category_goal') not in {'secure_supply', 'stabilise'}:
        return total_cost(case, terms, standard)
    rows = [estimates.get((supplier_id, p)) for p in case.get('parts', [])]
    if len(rows) != 1 or not rows[0]:
        return total_cost(case, terms, standard)
    row = rows[0]
    # Use the upper cost bound conservatively. Financing rate is explicitly a
    # buyer-rate proxy until supported supplier-specific financing data exists.
    model = {'standard': standard, 'full_cost': row['unit_cost'] * (1 + row['confidence_pct'] / 100),
             'interest_rate': case['buyer']['interest_rate']}
    if not all(k in standard for k in ['payment_days', 'incoterm']):
        return total_cost(case, terms, standard)
    return total_cost(case, terms, standard, model)
