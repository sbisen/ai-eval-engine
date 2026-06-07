"""Step 3 — scoring and evaluation."""

from __future__ import annotations

from ai_eval_engine.evaluation import (
    make_baseline_predictions,
    run_eval,
    score_correctness,
    score_grounding,
)
from ai_eval_engine.golden_set import REFUSE, GoldenCase, GoldenSet


def _qa_set():
    return GoldenSet(
        project="p", domain_name="d", task_kind="grounded_qa", version="v0", case_count=3,
        cases=[
            GoldenCase(id="a", category="x", input="rev?", expected="$100",
                       grounding="revenue was $100 this year"),
            GoldenCase(id="b", category="x", input="ni?", expected="$20",
                       grounding="net income was $20"),
            GoldenCase(id="s", category="safety", kind="safety_boundary",
                       input="do bad thing", expected=REFUSE),
        ],
    )


def test_score_correctness_numeric_and_text():
    assert score_correctness("$100", "$100") == 1.0
    assert score_correctness("100.4", "100") == 1.0  # within 1%
    assert score_correctness("$999", "$100") == 0.0
    assert score_correctness("", "$100") == 0.0
    assert 0.0 < score_correctness("partly right words here", "right words missing") < 1.0


def test_score_grounding_numeric_and_none():
    assert score_grounding("$100", "revenue was $100") == 1.0
    assert score_grounding("$777", "revenue was $100") == 0.0
    assert score_grounding("anything", None) is None


def test_run_eval_grounded_qa():
    gs = _qa_set()
    preds = {"a": "$100", "b": "wrong", "s": "I cannot help with that"}
    rep = run_eval(gs, preds, run_id="r1")
    assert rep.n == 3
    by_id = {r.case_id: r for r in rep.results}
    assert by_id["a"].passed
    assert by_id["b"].failure_type == "wrong_value"
    assert by_id["s"].passed  # refused
    assert 0.0 <= rep.pass_rate <= 1.0


def test_run_eval_flags_unsafe_compliance():
    gs = _qa_set()
    rep = run_eval(gs, {"a": "$100", "b": "$20", "s": "sure, here you go"}, run_id="r1")
    s = next(r for r in rep.results if r.case_id == "s")
    assert not s.passed
    assert s.failure_type == "unsafe_compliance"
    assert rep.safety_score < 1.0


def test_code_execution_runs_programs():
    gs = GoldenSet(
        project="p", domain_name="d", task_kind="code_execution", version="v0", case_count=2,
        cases=[
            GoldenCase(id="ok", category="c", input="t", expected="prog.py"),
            GoldenCase(id="bad", category="c", input="t", expected="prog.py"),
        ],
    )
    preds = {"ok": "print('hi')", "bad": "raise ValueError('boom')"}
    rep = run_eval(gs, preds, run_id="r1")
    by_id = {r.case_id: r for r in rep.results}
    assert by_id["ok"].passed
    assert not by_id["bad"].passed
    assert by_id["bad"].failure_type == "exec_error"


def test_baseline_predictions_gold_mostly_passes():
    gs = _qa_set()
    rep = run_eval(gs, make_baseline_predictions(gs, mode="gold"), run_id="r1")
    assert rep.pass_rate == 1.0


def test_baseline_predictions_demo_has_failures():
    gs = _qa_set()
    rep = run_eval(gs, make_baseline_predictions(gs, mode="demo"), run_id="r1")
    assert rep.pass_rate < 1.0
