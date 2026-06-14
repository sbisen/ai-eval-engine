"""Step 2 — golden-set generation."""

from __future__ import annotations

import json

import pytest

from ai_eval_engine.golden_set import (
    REFUSE,
    GeneratedCase,
    GeneratedGoldenSet,
    GoldenSet,
    LLMBackend,
    build_generation_message,
    build_golden_set,
    generate_golden_set,
    runbook_learnings,
)


class _FakeBackend(LLMBackend):
    """Returns a fixed GeneratedGoldenSet so the generative path runs offline."""

    def __init__(self, generated: GeneratedGoldenSet) -> None:
        self._generated = generated
        self.calls: list[dict] = []

    def parse(self, *, system, user, schema):
        self.calls.append({"system": system, "user": user, "schema": schema})
        return self._generated


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


# --- generative path (offline via a fake backend) ---------------------------


def _context_file(tmp_path):
    ctx = tmp_path / "ctx.json"
    ctx.write_text(json.dumps({
        "domain_name": "Finance QA",
        "summary": "open-book QA over filings",
        "categories": [{"name": "metrics-generated", "description": "compute a metric",
                        "example_queries": ["revenue?"]}],
        "safety_constraints": [
            {"name": "ground_figures", "description": "ground every figure in evidence",
             "severity": "high", "rationale": "regulated"},
        ],
        "quality_signals": [],
    }))
    return ctx


def test_generate_authors_varied_cases(qa_project, tmp_path):
    ctx = _context_file(tmp_path)
    generated = GeneratedGoldenSet(cases=[
        GeneratedCase(category="metrics-generated", kind="normal", difficulty="easy",
                      input="What was revenue?", expected="$100",
                      grounding="Total revenue was $100", rationale="baseline lookup"),
        GeneratedCase(category="metrics-generated", kind="ambiguous", difficulty="hard",
                      input="What is the margin?", expected="State which margin is meant.",
                      grounding="revenue $100; net income $20", rationale="undefined metric"),
        GeneratedCase(category="out_of_scope", kind="out_of_scope", difficulty="medium",
                      input="What is the FY2099 cash flow?", expected="ignored-overwritten",
                      grounding="not in the filing", rationale="unsupported period"),
    ])
    backend = _FakeBackend(generated)
    gs = generate_golden_set(qa_project, ctx, target_cases=3, backend=backend)

    kinds = {c.kind for c in gs.cases}
    assert kinds == {"normal", "ambiguous", "out_of_scope", "safety_boundary"}
    # out_of_scope expected is normalized to the REFUSE sentinel
    oos = next(c for c in gs.cases if c.kind == "out_of_scope")
    assert oos.expected == REFUSE
    # generated cases are marked and carry difficulty in notes
    assert all("generated" in c.notes for c in gs.cases if c.kind != "safety_boundary")
    assert any("difficulty=hard" in c.notes for c in gs.cases)
    # the deterministic safety floor is still appended from the context
    assert sum(c.kind == "safety_boundary" for c in gs.cases) == 1
    # the model actually received the generation schema
    assert backend.calls and backend.calls[0]["schema"] is GeneratedGoldenSet


def test_runbook_learnings_distils_open_items():
    runbook = {"items": [
        {"category": "Acme", "failure_type": "wrong_value", "occurrences": 3,
         "recommended_check": "tighten expected", "status": "open"},
        {"category": "Globex", "failure_type": "ungrounded", "occurrences": 1,
         "recommended_check": "require evidence", "status": "resolved"},
    ]}
    learnings = runbook_learnings(runbook)
    assert len(learnings) == 1  # resolved item is skipped
    assert learnings[0]["failure_type"] == "wrong_value"
    assert learnings[0]["occurrences"] == 3
    assert runbook_learnings(None) == []


def test_runbook_feedback_reaches_generation_prompt(qa_project, tmp_path):
    """The living runbook's failures must appear in the next generation prompt."""
    ctx = _context_file(tmp_path)
    runbook = tmp_path / "runbook.json"
    runbook.write_text(json.dumps({"items": [
        {"category": "metrics-generated", "failure_type": "wrong_value", "occurrences": 4,
         "recommended_check": "tighten the expected answer", "status": "open"},
    ]}))
    generated = GeneratedGoldenSet(cases=[
        GeneratedCase(category="metrics-generated", kind="normal", difficulty="easy",
                      input="What was revenue?", expected="$100",
                      grounding="Total revenue was $100", rationale="baseline"),
    ])
    backend = _FakeBackend(generated)
    generate_golden_set(qa_project, ctx, runbook_path=runbook, backend=backend)
    sent = backend.calls[0]["user"]
    assert "Prior eval learnings" in sent
    assert "wrong_value" in sent
    assert "tighten the expected answer" in sent


def test_generation_prompt_omits_learnings_when_absent(qa_project, tmp_path):
    ctx = json.loads(_context_file(tmp_path).read_text())
    msg = build_generation_message("p", ctx, [], 3, learnings=None)
    assert "Prior eval learnings" not in msg


def test_generated_set_is_versioned_and_roundtrips(qa_project, tmp_path):
    ctx = _context_file(tmp_path)
    generated = GeneratedGoldenSet(cases=[
        GeneratedCase(category="metrics-generated", kind="normal", difficulty="easy",
                      input="What was revenue?", expected="$100",
                      grounding="Total revenue was $100", rationale="baseline"),
    ])
    gs = generate_golden_set(qa_project, ctx, backend=_FakeBackend(generated))
    assert gs.version.startswith("v") and len(gs.version) == 11
    p = gs.save(tmp_path / "gen.json")
    assert GoldenSet.load(p).version == gs.version
    # ids are positionally assigned for the generated (non-safety) cases
    assert any(c.id.startswith("gen-") for c in gs.cases)
