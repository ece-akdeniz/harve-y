import pytest

from negotiator.state import Journal


@pytest.mark.parametrize("tail", [b'{"rec":', b'{"rec":"\xe2'])
def test_torn_last_record_repaired_before_appending(tmp_path, tail):
    path = tmp_path / "journal.jsonl"
    j = Journal(path)
    j.session("case:D02", "session-1")
    with path.open("ab") as stream:
        stream.write(tail)
    resumed = Journal(path)
    resumed.result("case:D02", "session-1", {"score": 0.5})
    again = Journal(path)
    assert again.session_for("case:D02") == "session-1"
    assert again.finished("case:D02") == {"score": 0.5}
    assert next(tmp_path.glob("*.torn-*")).read_bytes() == tail


def test_complete_last_record_without_newline(tmp_path):
    path = tmp_path / "journal.jsonl"
    path.write_text('{"rec":"session","case":"case:D02","session":"s"}')
    Journal(path).result("case:D02", "s", {"score": 1})
    assert Journal(path).finished("case:D02") == {"score": 1}


def test_mid_file_corruption_is_not_silently_discarded(tmp_path):
    path = tmp_path / "journal.jsonl"
    raw = b'{broken}\n{"rec":"session","case":"case:D02","session":"s"}\n'
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="before the last line"):
        Journal(path)
    assert path.read_bytes() == raw
