import copy

import pytest

from negotiator.lab.policy import default_suite, evaluate_campaign


def sample():
    suite = default_suite()
    checkpoint = {"published": True, "runner": "serial", "data": {}}
    attempts = [
        dict(
            attempt_id=f"{arm}-{case}-{repeat}",
            arm=arm,
            case_id=case,
            repeat=repeat,
            status="completed",
            score=0.6 if arm == "baseline" else 0.7,
            timeouts=0,
            result={"deal": True, "must_haves_ok": True, "ended": True},
            checkpoint_id=arm,
        )
        for repeat in range(1, 4)
        for case in suite["cases"]
        for arm in ("baseline", "candidate")
    ]
    return suite, checkpoint, attempts


def test_complete_sample_eligible():
    suite, checkpoint, attempts = sample()
    result = evaluate_campaign(suite, checkpoint, checkpoint, attempts)
    assert result["eligible"]
    assert result["metrics"]["gain"] == pytest.approx(10)


@pytest.mark.parametrize(
    "change",
    [
        dict(timeouts=None),
        dict(status="recovered"),
        dict(result={}),
        dict(result={"deal": True, "must_haves_ok": False}),
        dict(result={"deal": True, "must_haves_ok": True, "score": 0.1}),
    ],
)
def test_missing_or_invalid_evidence_blocks(change):
    suite, checkpoint, attempts = sample()
    attempts[1].update(change)
    assert not evaluate_campaign(suite, checkpoint, checkpoint, attempts)["eligible"]


def test_case_regression_and_duplicate_sample_block():
    suite, checkpoint, attempts = sample()
    for attempt in attempts:
        if attempt["arm"] == "candidate" and attempt["case_id"] == suite["cases"][0]:
            attempt["score"] = 0.55
    assert not evaluate_campaign(suite, checkpoint, checkpoint, attempts)["eligible"]
    attempts.append(copy.deepcopy(attempts[0]))
    assert not evaluate_campaign(suite, checkpoint, checkpoint, attempts)["eligible"]


def test_unknown_timeout_label_cannot_promote():
    suite, checkpoint, attempts = sample()
    attempts[1]["timeouts"] = "unknown"
    assert not evaluate_campaign(suite, checkpoint, checkpoint, attempts)["eligible"]
