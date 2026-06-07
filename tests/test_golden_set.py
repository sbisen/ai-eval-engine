"""Step 2 — golden-set generation."""

from __future__ import annotations

import json

import pytest

from ai_eval_engine.golden_set import REFUSE, GoldenSet, build_golden_set


def test_build_from_qa_project(qa_project):
    gs = build_golden_set(qa_project)
    assert gs.task_kind == "grounded_qa"
    assert gs.case_count == 4
    assert {c.category for c in gs.cases} == {"Acme", "Globex"}
    c = next(c for c in gs.cases if c.id == "case-q1")
    assert c.input == "What was revenue?"
    assert c.expected == "$100"
    assert c.grounding and "revenue" in c.grounding
    assert c.kind == "normal"


def test_version_is_deterministic(qa_project):
    assert build_golden_set(qa_project).version == build_golden_set(qa_project).version


def test_version_is_content_addressed(qa_project, tmp_path):
    gs = build_golden_set(qa_project)
    assert gs.version.startswith("v") and len(gs.version) == 11


def test_safety_cases_from_context(qa_project, tmp_path):
    ctx = tmp_path / "ctx.json"
    ctx.write_text(json.dumps({
        "domain_name": "Finance QA",
        "safety_constraints": [
            {"name": "no_advice", "description": "do not give personalized advice",
             "severity": "critical", "rationale": "regulated"},
        ],
    }))
    gs = build_golden_set(qa_project, context_path=ctx)
    assert gs.domain_name == "Finance QA"
    safety = [c for c in gs.cases if c.kind == "safety_boundary"]
    assert len(safety) == 1
    assert safety[0].expected == REFUSE
    assert "critical" in safety[0].notes


def test_save_load_roundtrip(qa_project, tmp_path):
    gs = build_golden_set(qa_project)
    p = gs.save(tmp_path / "g.json")
    assert GoldenSet.load(p).version == gs.version


def test_requires_task_spec(config_path):
    with pytest.raises(ValueError, match="config.task is required"):
        build_golden_set(config_path)
