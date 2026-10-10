"""tools/release_check.py: a fake Sunday overlay lists its new letter, flags unmatched phrasing, shows trait changes."""

import csv
import importlib.util
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_tool():
    spec = importlib.util.spec_from_file_location("release_check", ROOT / "tools/release_check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base_dir() -> Path:
    for c in (os.environ.get("ARENA_DATA"), "data/package", "/tmp/nak/data"):
        if c and (Path(c) / "facts.json").is_file():
            return Path(c).resolve()
    pytest.skip("data package not available")


NEW_LETTER = ("doc:20261011-70110-R1", "sup:70110", "Letter from the works manager",
              "Dear Sir or Madam, after the flood in our foundry hall we are running on one line and ask for "
              "patience with deliveries in November. Yours faithfully, Eisengießerei Hollerau GmbH")
KNOWN_PHRASING = ("doc:20261011-70110-R2", "sup:70110", "Call note",
                  "Call with the CFO. He said the bank is watching every month and asked whether we could pay "
                  "earlier against a discount.")
NEWS = ("news:20261011-90", "sup:70110", "flood_damage", "Flood stops one casting line at the Hollerau foundry")


def _write_release(tmp_path: Path) -> Path:
    release = tmp_path / "release-sunday"
    (release / "data").mkdir(parents=True)
    (release / "correspondence").mkdir()
    facts, rows = {}, []
    for ref, sid, title, text in (NEW_LETTER, KNOWN_PHRASING):
        path = f"correspondence/{ref.split(':', 1)[1]}.md"
        (release / path).write_text(f"# {title}\n\nletter - 2026-10-11 - supplier\n\n{text}\n")
        facts[ref] = {"date": "2026-10-11", "supplier": sid, "title": title, "type": "letter"}
        rows.append({"id": ref, "date": "2026-10-11", "kind": "letter", "supplier_id": sid, "subject": title,
                     "file": path})
    ref, sid, topic, headline = NEWS
    facts[ref] = {"date": "2026-10-11", "supplier": sid, "topic": topic, "headline": headline}
    facts["idx:AS-14404@2026-10"] = {"month": "2026-10", "series": "AS-14404", "value": 1234.5}
    (release / "facts.json").write_text(json.dumps(facts))
    with (release / "data/documents.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (release / "RELEASE.md").write_text("fake overlay for tests\n")
    return release


def test_release_overlay_lists_new_docs_and_flags_unmatched(tmp_path, capsys):
    tool = _load_tool()
    base = _base_dir()
    release = _write_release(tmp_path)
    cases = tool.load_cases(ROOT / "tests/fixtures/practice_cases.json", {"case:P01", "case:P18"})
    report = tool.run_check(str(base), str(release), cases=cases)

    assert report["release"] == str(release)
    assert [d["id"] for d in report["diff"]["new_docs"]["sup:70110"]] == [NEW_LETTER[0], KNOWN_PHRASING[0]]
    assert [n["id"] for n in report["diff"]["new_news"]["sup:70110"]] == [NEWS[0]]
    assert report["diff"]["new_index_months"] == {"AS-14404": ["2026-10"]}
    assert report["diff"]["new_ids"] == {"doc": [NEW_LETTER[0], KNOWN_PHRASING[0]], "idx": ["idx:AS-14404@2026-10"],
                                         "news": [NEWS[0]]}
    assert report["conflicts"] == []

    by_id = {n["id"]: n for n in report["notes"]}
    assert set(by_id) == {NEW_LETTER[0], KNOWN_PHRASING[0]}  # overlay scope only
    assert by_id[NEW_LETTER[0]]["traits"] == [] and not by_id[NEW_LETTER[0]]["skipped"]
    assert by_id[NEW_LETTER[0]]["preview"].startswith("Dear Sir or Madam, after the flood")
    assert by_id[KNOWN_PHRASING[0]]["traits"] == ["liquidity_crisis"]
    assert report["unmatched_notes"] == [NEW_LETTER[0]]
    assert report["news_topics_untracked"] == {"flood_damage": [NEWS[0]]}
    assert report["news_topics_new"] == ["flood_damage"]

    assert report["trait_changes"] == {"sup:70110": {"added": ["liquidity_crisis"], "removed": []}}
    p01 = next(c for c in report["cases"] if c["case_id"] == "case:P01")
    assert p01["changed"] and p01["suppliers"]["sup:70110"]["gained"] == ["liquidity_crisis"]
    p18 = next(c for c in report["cases"] if c["case_id"] == "case:P18")
    assert p18["suppliers"]["sup:70740"]["gained"] == []
    assert isinstance(p18["bank_size"]["base"], int) and isinstance(p18["bank_size"]["release"], int)

    assert f"note {NEW_LETTER[0]} matches no NOTE_TRAITS" in report["warn"]
    assert "news topic 'flood_damage' not in NEWS_TRAITS (1 items)" in report["warn"]
    assert "no release overlay" not in report["warn"]

    tool.print_report(report)
    out = capsys.readouterr().out
    assert f"WARN  {NEW_LETTER[0]}" in out and "NO TRAIT" in out
    assert "sup:70110  +['liquidity_crisis']" in out
    assert "CHANGED case:P01" in out


def test_no_release_runs_base_coverage(tmp_path):
    tool = _load_tool()
    base = _base_dir()
    cases = tool.load_cases(ROOT / "tests/fixtures/practice_cases.json", {"case:P04"})
    report = tool.run_check(str(base), str(tmp_path / "missing"), cases=cases)
    assert report["release"] is None
    assert report["notes_scope"] == "all"
    assert "no release overlay" in report["warn"]
    assert len(report["notes"]) > 100  # every base note was checked
    assert all(n["traits"] for n in report["notes"] if n["id"].endswith("-M1"))  # v1 meeting notes still match
    assert report["trait_changes"] == {}
    assert all(not c["changed"] for c in report["cases"])
    assert report["model_proposals"] is None


def test_model_proposals_keep_only_verbatim_quotes():
    tool = _load_tool()
    rows = [{"id": "doc:x", "date": "2026-10-11", "subject": "Letter",
             "text": "We are running on one line and ask for patience with deliveries."}]
    answer = json.dumps({"proposals": [
        {"trait": "reduced_capacity", "quote": "running on one line"},
        {"trait": "idle_capacity", "quote": "this sentence is not in the note"},
        {"trait": "Bad Name", "quote": "running on one line"},
    ]})
    proposals = tool.propose_traits(rows, complete=lambda prompt: answer)
    assert proposals == [{"id": "doc:x", "trait": "reduced_capacity", "quote": "running on one line", "known": False}]
    assert tool.propose_traits(rows, complete=lambda prompt: "not json") == [{"id": "doc:x", "error": "Expecting "
                                                                              "value: line 1 column 1 (char 0)"}]
