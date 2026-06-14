"""The Domain-Compliance Runbook — the single living domain file (Facts · Criteria · Modes)."""

from __future__ import annotations

from ai_eval_engine.domain_compliance_runbook import (
    DomainComplianceRunbook,
    build_compliance_runbook,
)
from ai_eval_engine.domain_context import DomainContext
from ai_eval_engine.evaluation import run_eval
from ai_eval_engine.golden_set import GoldenCase, GoldenSet
from ai_eval_engine.eval_learnings import Runbook, update_runbook

CTX = {
    "domain_name": "Fin",
    "summary": "filings QA",
    "domain_facts": [
        {"group": "definition", "label": "working capital",
         "detail": "operating working capital, excluding cash", "provenance": "curated"},
        {"group": "unit", "label": "scale", "detail": "USD millions", "provenance": "seeded"},
    ],
    "categories": [{"name": "metrics", "description": "compute a ratio", "example_queries": []}],
    "quality_signals": [{"name": "rounding", "description": "respect stated rounding"}],
    "safety_constraints": [
        {"name": "ground_every_figure", "description": "trace each number",
         "severity": "critical", "rationale": "hallucinated figures are the worst failure"},
    ],
}


def _runbook_with_a_failure() -> Runbook:
    gs = GoldenSet(
        project="fin", domain_name="Fin", task_kind="grounded_qa", version="v0", case_count=2,
        cases=[
            GoldenCase(id="a", category="metrics", input="q", expected="$1", grounding="$1 here"),
            GoldenCase(id="b", category="metrics", input="q", expected="$2", grounding="$2 here"),
        ],
    )
    rep = run_eval(gs, {"a": "$1", "b": "wrong"}, run_id="run-0001")
    return update_runbook(Runbook(project="fin"), rep)


def test_three_sections_in_fixed_order():
    cr = build_compliance_runbook(CTX, _runbook_with_a_failure(), "fin", "Fin")
    assert [s.key for s in cr.sections] == ["facts", "criteria", "modes"]
    assert [s.title for s in cr.sections] == [
        "Domain Facts", "Domain Compliance Key Criteria", "Common Failure Modes",
    ]


def test_facts_are_seeded_itemized_and_grouped():
    cr = build_compliance_runbook(CTX, Runbook(project="fin"), "fin", "Fin")
    facts = next(s for s in cr.sections if s.key == "facts")
    groups = {e.group for e in facts.entries}
    # definitions/units, the categories, and the data signals all itemize into the facts tree
    assert {"Definitions", "Units & rounding", "Question categories", "Data characteristics"} <= groups
    wc = next(e for e in facts.entries if e.label == "working capital")
    assert wc.tag == "curated"  # provenance is surfaced as the chip


def test_failure_modes_grow_from_eval_results_and_are_empty_on_a_clean_run():
    grown = build_compliance_runbook(CTX, _runbook_with_a_failure(), "fin", "Fin")
    modes = next(s for s in grown.sections if s.key == "modes")
    assert modes.entries and modes.entries[0].count >= 1

    clean = build_compliance_runbook(CTX, Runbook(project="fin"), "fin", "Fin")
    clean_modes = next(s for s in clean.sections if s.key == "modes")
    assert clean_modes.entries == []  # nothing learned yet — Facts/Criteria still seeded


def test_save_and_load_round_trips(tmp_path):
    cr = build_compliance_runbook(CTX, _runbook_with_a_failure(), "fin", "Fin")
    path = cr.save(tmp_path / "domain_compliance_runbook.json")
    again = DomainComplianceRunbook.load(path)
    assert again.model_dump() == cr.model_dump()


def test_domain_context_parses_with_and_without_domain_facts():
    # back-compat: older contexts had no domain_facts field
    bare = DomainContext(domain_name="d", summary="s", categories=[],
                         safety_constraints=[], quality_signals=[])
    assert bare.domain_facts == []
    rich = DomainContext(domain_name="d", summary="s", categories=[],
                         domain_facts=[{"label": "wc", "detail": "operating WC"}],
                         safety_constraints=[], quality_signals=[])
    assert rich.domain_facts[0].provenance == "seeded"  # default
