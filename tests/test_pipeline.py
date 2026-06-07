"""End-to-end pipeline (Steps 2-5) and the build CLI."""

from __future__ import annotations

import json

from ai_eval_engine.cli import main
from ai_eval_engine.evaluation import EvalReport
from ai_eval_engine.pipeline import build
from ai_eval_engine.runbook import Runbook


def test_build_emits_all_artifacts(qa_project, tmp_path):
    out = tmp_path / "out"
    paths = build(qa_project, out)
    for key in ("golden_set", "eval_script", "predictions", "eval_report",
                "runbook", "dashboard"):
        assert paths[key].exists(), key
    assert (out / "index.html").read_text().startswith("<!doctype html>")
    assert "def predict" in paths["eval_script"].read_text()


def test_build_accumulates_runs(qa_project, tmp_path):
    out = tmp_path / "out"
    build(qa_project, out)
    build(qa_project, out)
    runs = list((out / "runs").glob("run-*.json"))
    assert len(runs) == 2
    rb = Runbook.load(out / "runbook.json")
    assert rb.runs == ["run-0001", "run-0002"]
    # an item seen in both runs has its occurrences accumulated
    assert any(it.occurrences >= 2 for it in rb.items)


def test_build_with_explicit_predictions(qa_project, tmp_path):
    out = tmp_path / "out"
    # all-correct predictions -> perfect pass rate, empty runbook
    preds = {"case-q1": "$100", "case-q2": "$20", "case-q3": "Three",
             "case-q4": "Refer to filing"}
    build(qa_project, out, predictions=preds)
    rep = EvalReport.load(out / "eval_report.json")
    assert rep.pass_rate == 1.0
    assert Runbook.load(out / "runbook.json").items == []


def test_cli_build(qa_project, tmp_path, capsys):
    out = tmp_path / "cliout"
    rc = main(["build", "--config", str(qa_project), "--out", str(out)])
    assert rc == 0
    assert (out / "index.html").exists()


def test_cli_golden_json(qa_project, capsys):
    rc = main(["golden", "--config", str(qa_project)])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["task_kind"] == "grounded_qa"
    assert payload["case_count"] == 4
