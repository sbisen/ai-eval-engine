"""End-to-end pipeline: golden set → eval → runbook → dashboard.

:func:`build` runs Steps 2–5 and drops every artifact into an output directory,
so a user can go from a CSV + config to a full domain-aware eval bundle with one
call. It is fully offline and deterministic when ``demo=True`` (synthetic
baseline predictions); pass a real predictions map/file to score an actual agent.
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_eval_engine.dashboard import render_dashboard
from ai_eval_engine.eval_script import generate_eval_script
from ai_eval_engine.evaluation import EvalReport, make_baseline_predictions, run_eval
from ai_eval_engine.golden_set import GoldenSet, build_golden_set
from ai_eval_engine.runbook import Runbook, update_runbook


def _next_run_id(runs_dir: Path) -> str:
    n = len(list(runs_dir.glob("run-*.json"))) if runs_dir.exists() else 0
    return f"run-{n + 1:04d}"


def build(
    config_path: str | Path,
    out_dir: str | Path,
    context_path: str | Path | None = None,
    predictions: dict[str, str] | str | Path | None = None,
    demo: bool = True,
    run_id: str | None = None,
) -> dict[str, Path]:
    """Run Steps 2–5 and write all artifacts under ``out_dir``.

    Artifacts: ``golden_set.json``, ``eval_<project>.py``, ``predictions.json``,
    ``runs/<run_id>.json``, ``runbook.json``, ``index.html``.
    """
    out = Path(out_dir)
    runs = out / "runs"
    runs.mkdir(parents=True, exist_ok=True)

    # Step 2 — golden set
    golden: GoldenSet = build_golden_set(config_path, context_path=context_path)
    golden_path = golden.save(out / "golden_set.json")

    # Step 3 — runnable eval script artifact
    script_path = out / f"eval_{golden.project}.py"
    script_path.write_text(generate_eval_script(golden.project))

    # predictions: explicit map / file, else synthetic baseline
    if isinstance(predictions, (str, Path)):
        preds = json.loads(Path(predictions).read_text())
    elif isinstance(predictions, dict):
        preds = predictions
    else:
        preds = make_baseline_predictions(golden, mode="demo" if demo else "gold")
    preds_path = out / "predictions.json"
    preds_path.write_text(json.dumps(preds, indent=2))

    # Step 3 — score
    rid = run_id or _next_run_id(runs)
    report: EvalReport = run_eval(golden, preds, run_id=rid)
    report.save(runs / f"{rid}.json")
    report.save(out / "eval_report.json")  # latest, convenient

    # Step 4 — runbook (accumulates across runs)
    runbook: Runbook = Runbook.load_or_new(out / "runbook.json", golden.project)
    runbook = update_runbook(runbook, report)
    runbook_path = runbook.save(out / "runbook.json")

    # Step 5 — dashboard over full run history
    history = sorted(
        (EvalReport.load(p) for p in runs.glob("run-*.json")), key=lambda r: r.run_id
    )
    dash_path = render_dashboard(history, runbook, out / "index.html")

    return {
        "golden_set": golden_path,
        "eval_script": script_path,
        "predictions": preds_path,
        "eval_report": runs / f"{rid}.json",
        "runbook": runbook_path,
        "dashboard": dash_path,
    }
