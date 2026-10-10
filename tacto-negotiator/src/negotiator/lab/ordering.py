"""One deterministic interleaving for the server plan and both local runners."""

import random


def campaign_order(cases, repetitions, seed, arms=("baseline", "candidate")):
    rng = random.Random(seed)
    cells = []
    for repeat in range(1, repetitions + 1):
        for case in cases:
            order = list(arms)
            rng.shuffle(order)
            cells.extend(dict(arm=arm, case_id=case, repeat=repeat) for arm in order)
    return cells
