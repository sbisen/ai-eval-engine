"""End-to-end pipeline: golden set → eval → runbook → dashboard.

:func:`build` runs Steps 2–5 and drops every artifact into an output directory,
so a user can go from a CSV + config to a full domain-aware eval bundle with one
call. It is fully offline and deterministic when ``demo=True`` (synthetic
baseline predictions); pass a real predictions map/file to score an actual agent.
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_eval_engine.domain_compliance_runbook import (
    build_compliance_check,
    build_compliance_runbook,
)
from ai_eval_engine.dashboard import render_dashboard
from ai_eval_engine.evaluation import (
    EvalReport,
    generate_eval_script,
    make_baseline_predictions,
    run_eval,
)
from ai_eval_engine.golden_set import GoldenSet, build_golden_set
from ai_eval_engine.eval_learnings import Runbook, update_runbook


def _next_run_id(runs_dir: Path) -> str:
    n = len(list(runs_dir.glob("run-*.json"))) if runs_dir.exists() else 0
    return f"run-{n + 1:04d}"


def _rerun_command(
    config_path: str | Path,
    out_dir: str | Path,
    context_path: str | Path | None,
    predictions: dict[str, str] | str | Path | None,
) -> str:
    """The exact ``ai-eval-engine build`` line that regenerates this bundle, shown in the
    dashboard so anyone can rerun the whole pipeline. Only file-backed predictions are
    echoed (an inline dict has no command-line form)."""
    parts = ["ai-eval-engine build", f"--config {config_path}", f"--out {out_dir}"]
    if context_path is not None:
        parts.append(f"--context {context_path}")
    if isinstance(predictions, (str, Path)):
        parts.append(f"--predictions {predictions}")
    return " ".join(parts)


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
    ``runs/<run_id>.json``, ``runbook.json``, ``domain_compliance_runbook.json``,
    ``index.html``.
    """
    out = Path(out_dir)
    runs = out / "runs"
    runs.mkdir(parents=True, exist_ok=True)

    # Step 2 — golden set
    golden: GoldenSet = build_golden_set(config_path, context_path=context_path)
    golden_path = golden.save(out / "golden_set.json")

    # Domain context for the Domain-Compliance Runbook: load it, or derive a minimal
    # one from the golden set's categories when no Step-1 context was provided.
    if context_path is not None:
        ctx = json.loads(Path(context_path).read_text())
    else:
        cats = sorted({c.category for c in golden.cases})
        ctx = {"domain_name": golden.domain_name,
               "categories": [{"name": c} for c in cats]}

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

    # The single living domain file: Step-1 Facts + Criteria seeded, Failure Modes grown.
    compliance = build_compliance_runbook(
        ctx if isinstance(ctx, dict) else None, runbook,
        golden.project, golden.domain_name,
    )
    compliance_path = compliance.save(out / "domain_compliance_runbook.json")

    # Step 5 — dashboard over full run history
    history = sorted(
        (EvalReport.load(p) for p in runs.glob("run-*.json")), key=lambda r: r.run_id
    )
    compliance_check = build_compliance_check(
        ctx if isinstance(ctx, dict) else None, report
    )
    rerun_cmd = _rerun_command(config_path, out_dir, context_path, predictions)
    dash_path = render_dashboard(
        history, runbook, out / "index.html",
        runbook_sections=compliance.as_dashboard_sections(),
        compliance_check=compliance_check,
        golden=golden, rerun_cmd=rerun_cmd,
    )

    return {
        "golden_set": golden_path,
        "eval_script": script_path,
        "predictions": preds_path,
        "eval_report": runs / f"{rid}.json",
        "runbook": runbook_path,
        "domain_compliance_runbook": compliance_path,
        "dashboard": dash_path,
    }
