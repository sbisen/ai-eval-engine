"""Step 4 — the accumulating runbook."""

from __future__ import annotations

from ai_eval_engine.evaluation import run_eval
from ai_eval_engine.golden_set import REFUSE, GoldenCase, GoldenSet
from ai_eval_engine.eval_learnings import Runbook, update_runbook


def _set():
    return GoldenSet(
        project="p", domain_name="d", task_kind="grounded_qa", version="v0", case_count=2,
        cases=[
            GoldenCase(id="b", category="x", input="q", expected="$20", grounding="net $20"),
            GoldenCase(id="s", category="safety", kind="safety_boundary", input="bad",
                       expected=REFUSE),
        ],
    )


def _failing_report(run_id):
    gs = _set()
    return run_eval(gs, {"b": "wrong", "s": "sure here you go"}, run_id=run_id)


def test_update_creates_items():
    rb = update_runbook(Runbook(project="p"), _failing_report("r1"))
    assert rb.runs == ["r1"]
    kinds = {it.failure_type for it in rb.items}
    assert "wrong_value" in kinds
    assert "unsafe_compliance" in kinds


def test_occurrences_accumulate_across_runs():
    rb = Runbook(project="p")
    update_runbook(rb, _failing_report("r1"))
    update_runbook(rb, _failing_report("r2"))
    safety = next(it for it in rb.items if it.failure_type == "unsafe_compliance")
    assert safety.occurrences == 2
    assert safety.first_seen == "r1"
    assert safety.last_seen == "r2"
    assert rb.runs == ["r1", "r2"]


def test_critical_sorts_first():
    rb = update_runbook(Runbook(project="p"), _failing_report("r1"))
    assert rb.items[0].severity == "critical"  # unsafe_compliance


def test_save_load_roundtrip(tmp_path):
    rb = update_runbook(Runbook(project="p"), _failing_report("r1"))
    p = rb.save(tmp_path / "rb.json")
    assert Runbook.load(p).items[0].id == rb.items[0].id


def test_load_or_new(tmp_path):
    rb = Runbook.load_or_new(tmp_path / "missing.json", "p")
    assert rb.project == "p" and rb.items == []
