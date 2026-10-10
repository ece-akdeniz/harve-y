"""Bounded, pure first-package preferences; no historical claims or supplier matching."""

import itertools
import math

from arena_kit.cost import complete_offer, must_haves_ok, total_cost

from .memory import FIELDS, validate_memory


def prefer_package(case, nonprice, reference_price, standard=None, supplier=None, *, memory=None):
    """Return (nonprice terms, citation trace or None), abstaining on unsupported input.

    Enumerate only currently negotiable lesson fields; preserve every unrelated
    field. A preference can break ties or lower cost, never increase complete
    buyer cost at the current reference price. No lab access or supplier IDs enter
    matching. The caller validates memory at startup and applies this once.
    """
    if memory is None:
        return nonprice, None
    try:
        snapshot = validate_memory(memory)
        options = case.get('term_options') or {}
        lessons = [lesson for lesson in snapshot['lessons'] if lesson['field'] in case['negotiable']
                   and lesson['field'] in nonprice and options.get(lesson['field'])]
        if not lessons or type(reference_price) not in (int, float) or not math.isfinite(reference_price):
            return nonprice, None
        fields = [lesson['field'] for lesson in lessons]
        for field in fields:
            if not isinstance(options[field], list) or any(
                type(value) is not int or not 0 <= value <= FIELDS[field] for value in options[field]
            ):
                return nonprice, None
        if math.prod(len(options[field]) for field in fields) > 4096:
            return nonprice, None
        base = {**nonprice, 'unit_price': reference_price}
        if set(base) != set(case['negotiable']) or complete_offer(case, base) != base:
            return nonprice, None
        if not must_haves_ok(case, base, standard):
            return nonprice, None
        base_cost = total_cost(case, base, standard, supplier)
        if not math.isfinite(base_cost):
            return nonprice, None

        def rank(terms):
            return tuple(terms[lesson['field']] * (1 if lesson['direction'] == 'higher' else -1)
                         for lesson in lessons)

        selected, selected_rank = base, rank(base)
        for values in itertools.product(*(options[field] for field in fields)):
            trial = {**base, **dict(zip(fields, values, strict=True))}
            if complete_offer(case, trial) != trial or not must_haves_ok(case, trial, standard):
                continue
            cost = total_cost(case, trial, standard, supplier)
            trial_rank = rank(trial)
            # Do not sacrifice one supported preference to improve another.
            if (math.isfinite(cost) and cost <= base_cost
                    and all(a >= b for a, b in zip(trial_rank, rank(base), strict=True))
                    and trial_rank > selected_rank):
                selected, selected_rank = trial, trial_rank
        affected = [lesson for lesson in lessons if selected[lesson['field']] != base[lesson['field']]]
        if not affected:
            return nonprice, None
        return {k: v for k, v in selected.items() if k != 'unit_price'}, dict(
            snapshot_id=snapshot['snapshot_id'],
            lesson_ids=[lesson['lesson_id'] for lesson in affected],
            evidence_ids=sorted({key for lesson in affected for key in lesson['evidence_ids']}),
        )
    except (KeyError, TypeError, ValueError, ArithmeticError):
        return nonprice, None
