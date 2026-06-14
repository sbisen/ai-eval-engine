"""Step 4 — Living Runbook.

The living record of what the agent-under-test gets *wrong*. After each
eval it reads the scorer's failures and writes down the learning: failures are
clustered by (category, failure_type) into stable, content-addressed items, each
carrying a ``recommended_check`` — the concrete golden-set addition that would
catch this failure next time. Re-running merges into the existing runbook:
occurrence counts grow, ``last_seen`` advances, and example case ids accrue, so the
runbook accumulates learnings across runs rather than being a one-shot dump.

This artifact closes the loop: it is fed back as an input to the next golden-set
generation (see :func:`ai_eval_engine.golden_set.generate_golden_set`'s
``runbook`` argument), so recurring failure modes become targeted new cases.

Note on terminology: the clustering and ``recommended_check`` mapping are
deterministic rules, not a learned model — "learning" here means the accumulated,
human-reviewable record of failure modes, not gradient-based training.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel, Field

from ai_eval_engine.evaluation import SEVERITY, EvalReport

RECOMMENDED_CHECK = {
    "unsafe_compliance": "Add a refusal assertion for this safety boundary to the golden set.",
    "exec_error": "Capture the traceback; add a regression case pinning the failing input.",
    "ungrounded": "Require the answer's key figures to appear in the cited evidence.",
    "wrong_value": "Tighten the expected answer; review for ambiguous phrasing.",
    "empty_answer": "Treat empty output as a hard failure; check the agent's timeout/limits.",
    "wrong_format": "Add a format/schema validation step before scoring.",
}
_STATUS_BY_SEVERITY = {"critical": "open", "high": "open", "medium": "monitoring",
                       "low": "monitoring"}


class RunbookItem(BaseModel):
    id: str
    title: str
    category: str
    failure_type: str
    severity: str
    occurrences: int = 0
    first_seen: str = ""
    last_seen: str = ""
    example_case_ids: list[str] = Field(default_factory=list)
    status: str = "open"
    recommended_check: str = ""


class Runbook(BaseModel):
    project: str
    runs: list[str] = Field(default_factory=list)
    items: list[RunbookItem] = Field(default_factory=list)

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2))
        return path

    @classmethod
    def load(cls, path: str | Path) -> "Runbook":
        return cls.model_validate_json(Path(path).read_text())

    @classmethod
    def load_or_new(cls, path: str | Path, project: str) -> "Runbook":
        p = Path(path)
        return cls.load(p) if p.exists() else cls(project=project)


def _item_id(category: str, failure_type: str) -> str:
    return "rb-" + hashlib.sha256(f"{category}::{failure_type}".encode()).hexdigest()[:8]


_SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def aggregate_failure_modes(runbook: "Runbook") -> list[dict]:
    """Collapse the flat per-(category, failure_type) items into failure *modes*,
    dropping the per-company split, severity-then-frequency ordered.

    Each mode dict: ``failure_type, severity, occurrences, categories, case_ids,
    recommended_check``. Consumed by :func:`ai_eval_engine.domain_compliance_runbook.\
build_compliance_runbook` to render the Failure Modes section. Deterministic — not learned.
    """
    modes: dict[str, dict] = {}
    for it in runbook.items:
        m = modes.setdefault(it.failure_type, {
            "failure_type": it.failure_type, "severity": it.severity,
            "occurrences": 0, "categories": [], "case_ids": [],
            "recommended_check": it.recommended_check,
        })
        m["occurrences"] += it.occurrences
        if it.category not in m["categories"]:
            m["categories"].append(it.category)
        m["case_ids"] += it.example_case_ids
        if _SEV_RANK.get(it.severity, 9) < _SEV_RANK.get(m["severity"], 9):
            m["severity"] = it.severity
    return sorted(modes.values(),
                  key=lambda m: (_SEV_RANK.get(m["severity"], 9), -m["occurrences"]))


def update_runbook(runbook: Runbook, report: EvalReport) -> Runbook:
    """Merge a report's failures into the runbook in place and return it."""
    if report.run_id not in runbook.runs:
        runbook.runs.append(report.run_id)
    index = {it.id: it for it in runbook.items}

    clusters: dict[tuple[str, str], list[str]] = {}
    for r in report.results:
        if r.failure_type:
            clusters.setdefault((r.category, r.failure_type), []).append(r.case_id)

    for (category, failure_type), case_ids in clusters.items():
        iid = _item_id(category, failure_type)
        severity = SEVERITY.get(failure_type, "medium")
        item = index.get(iid)
        if item is None:
            item = RunbookItem(
                id=iid,
                title=f"{failure_type.replace('_', ' ')} in {category}",
                category=category,
                failure_type=failure_type,
                severity=severity,
                first_seen=report.run_id,
                status=_STATUS_BY_SEVERITY.get(severity, "open"),
                recommended_check=RECOMMENDED_CHECK.get(failure_type, "Review failing cases."),
            )
            runbook.items.append(item)
            index[iid] = item
        item.occurrences += len(case_ids)
        item.last_seen = report.run_id
        merged = list(dict.fromkeys(item.example_case_ids + case_ids))
        item.example_case_ids = merged[:5]

    # Highest-severity, most-frequent first.
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    runbook.items.sort(key=lambda it: (order.get(it.severity, 9), -it.occurrences))
    return runbook
