"""Step 5 — the HTML dashboard."""

from __future__ import annotations

import pytest

from ai_eval_engine.dashboard import render_dashboard
from ai_eval_engine.evaluation import run_eval
from ai_eval_engine.golden_set import GoldenCase, GoldenSet
from ai_eval_engine.runbook import Runbook, update_runbook


def _report(run_id):
    gs = GoldenSet(
        project="dash", domain_name="d", task_kind="grounded_qa", version="v0", case_count=2,
        cases=[
            GoldenCase(id="a", category="x", input="q", expected="$1", grounding="$1 here"),
            GoldenCase(id="b", category="y", input="q", expected="$2", grounding="$2 here"),
        ],
    )
    return run_eval(gs, {"a": "$1", "b": "wrong"}, run_id=run_id)


def test_render_writes_self_contained_html(tmp_path):
    rep = _report("r1")
    rb = update_runbook(Runbook(project="dash"), rep)
    out = render_dashboard([rep], rb, tmp_path / "index.html")
    html = out.read_text()
    assert out.exists()
    assert "Domain Accuracy" in html
    assert "Safety runbook" in html
    assert "dash" in html
    assert "http://" not in html and "https://" not in html  # no external assets


def test_render_includes_trend_across_runs(tmp_path):
    reps = [_report("r1"), _report("r2"), _report("r3")]
    out = render_dashboard(reps, Runbook(project="dash"), tmp_path / "i.html")
    assert out.read_text().count('class="b"') == 3


def test_render_requires_a_report(tmp_path):
    with pytest.raises(ValueError):
        render_dashboard([], None, tmp_path / "i.html")
