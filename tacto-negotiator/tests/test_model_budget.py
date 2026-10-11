import concurrent.futures
import json

from negotiator.model_budget import SessionModelBudget


def test_shared_roles_and_restart_cannot_reset_reservations(tmp_path):
    journal = tmp_path / "transport.jsonl"
    budget = SessionModelBudget(max_calls=3, total_s=16)
    budget.bind("session:one", journal)
    assert budget.reserve("strategy", "sup:a", "update:1", "request:1", 8,
                          remaining_s=60)[0]
    assert (tmp_path / "model-budget.jsonl").stat().st_mode & 0o077 == 0
    assert not budget.reserve("writer", "sup:a", "update:1", "request:2", 6,
                              remaining_s=60, optional=True)[0]
    assert budget.reserve("final", "sup:a", "update:2", "request:3", 8,
                          remaining_s=60)[0]
    resumed = SessionModelBudget(max_calls=3, total_s=16)
    resumed.bind("session:one", journal)
    assert resumed.metrics()["calls"] == 2
    assert resumed.reserve("writer", "sup:b", "update:3", "request:4", 6,
                            remaining_s=60, optional=True)[1] == "budget_exhausted"
    assert resumed.reserve("strategy", "sup:a", "update:1", "request:1", 8,
                            remaining_s=60)[1] == "already_reserved"
    assert SessionModelBudget().metrics()["calls"] == 0


def test_concurrent_suppliers_share_atomic_budget(tmp_path):
    journal = tmp_path / "transport.jsonl"
    budgets = [SessionModelBudget(max_calls=3, total_s=24) for _ in range(6)]
    for budget in budgets:
        budget.bind("session:one", journal)

    def reserve(index):
        return budgets[index].reserve("writer", f"sup:{index}", f"update:{index}",
                                      f"request:{index}", 6, remaining_s=60)[0]

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        assert sum(pool.map(reserve, range(6))) == 3
    resumed = SessionModelBudget(max_calls=3, total_s=24)
    resumed.bind("session:one", journal)
    assert resumed.metrics()["calls"] == 3


def test_deadline_and_optional_decision_reserve(tmp_path):
    budget = SessionModelBudget(max_calls=4, total_s=20)
    budget.bind("session:one", tmp_path / "transport.jsonl")
    assert budget.reserve("writer", "sup:a", "u", "r", 6, remaining_s=24,
                          optional=True)[1] == "deadline_reserve"
    assert budget.reserve("writer", "sup:a", "u", "r", 6, remaining_s=60,
                          optional=True)[0]
    assert budget.reserve("writer", "sup:a", "u2", "r2", 6, remaining_s=60,
                          optional=True)[0]
    assert budget.reserve("writer", "sup:a", "u3", "r3", 6, remaining_s=60,
                          optional=True)[1] == "decision_budget_reserved"


def test_validation_call_is_reserved_and_charged_in_same_session(tmp_path):
    budget = SessionModelBudget(max_calls=4, total_s=22, validation_reserve_s=6)
    budget.bind("session:one", tmp_path / "transport.jsonl")
    assert budget.reserve("strategy", "sup:a", "u1", "r1", 8, remaining_s=60)[0]
    assert budget.reserve("final", "sup:a", "u2", "r2", 8, remaining_s=60)[0]
    assert budget.reserve("writer", "sup:a", "u3", "r3", 6, remaining_s=60)[1] == "validation_budget_reserved"
    assert budget.reserve("validation-repair-v1", "sup:a", "repair", "r4", 6,
                          remaining_s=60)[0]
    assert budget.metrics()["by_role"]["validation-repair-v1"]["calls"] == 1


def test_private_artifact_is_bounded_and_owner_only(tmp_path):
    budget = SessionModelBudget()
    budget.bind("session:one", tmp_path / "transport.jsonl")
    budget.artifact("writer", "digest", {"body": "x" * 20000}, response={"body": "y" * 20000})
    artifact = next((tmp_path / "model-evidence").iterdir())
    data = json.loads(artifact.read_text())
    assert len(data["request"]) <= 16000 and len(data["response"]) <= 16000
    assert artifact.stat().st_mode & 0o077 == 0


def test_different_sessions_share_file_without_sharing_allowance(tmp_path):
    journal = tmp_path / "transport.jsonl"
    first = SessionModelBudget(max_calls=1)
    first.bind("session:one", journal)
    assert first.reserve("strategy", "sup:a", "u", "r", 8, remaining_s=60)[0]
    second = SessionModelBudget(max_calls=1)
    second.bind("session:two", journal)
    assert second.metrics()["calls"] == 0
    assert second.reserve("strategy", "sup:b", "u", "r", 8, remaining_s=60)[0]
    assert SessionModelBudget(max_calls=1).metrics()["calls"] == 0


def test_corrupt_ledger_denies_new_calls(tmp_path):
    journal = tmp_path / "transport.jsonl"
    (tmp_path / "model-budget.jsonl").write_text('{"record":"model_reservation"\n')
    budget = SessionModelBudget()
    budget.bind("session:one", journal)
    assert budget.reserve("strategy", "sup:a", "u", "r", 8,
                          remaining_s=60)[1] == "ledger_corrupt"
