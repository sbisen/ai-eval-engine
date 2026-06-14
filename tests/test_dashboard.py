"""Step 5 — the HTML dashboard."""

from __future__ import annotations

import pytest

from ai_eval_engine.dashboard import render_dashboard
from ai_eval_engine.evaluation import run_eval
from ai_eval_engine.golden_set import GoldenCase, GoldenSet
from ai_eval_engine.eval_learnings import Runbook, update_runbook


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
    assert "Domain-Compliance Runbook" in html
    assert "dash" in html
    assert "http://" not in html and "https://" not in html  # no external assets


def test_okr_cards_are_the_fixed_two(tmp_path):
    """Step-5 shows two scalar cards — Domain Accuracy and Avg Confidence.
    Scope is not a card: it leads the Compliance checklist, so a Scope Safeguard card
    would just duplicate it. The old Pass Rate / Safety Score / Avg Consistency are gone,
    and Compliance is the checklist below, not a single-number card."""
    rep = _report("r1")
    out = render_dashboard([rep], None, tmp_path / "i.html")
    html = out.read_text()
    for lab in ("Domain Accuracy", "Avg Confidence Score"):
        assert lab in html, lab
    assert "North Star" not in html      # the North Star badge was removed
    assert "Pass Rate" not in html       # removed: it duplicated Domain Accuracy
    assert "Safety Score" not in html    # removed: replaced by the Compliance checklist
    assert "Avg Consistency" not in html  # removed earlier
    assert "Scope Safeguard" not in html  # removed: scope leads the Compliance checklist
    assert '<div class="l">Compliance</div>' not in html  # not a card anymore


def test_scope_rule_reports_refused_boundary_probes(tmp_path):
    """Scope lives in the Compliance checklist now (row 1), and its note still counts the
    off-domain probes the agent refused — honestly, with no fabricated number when none ran."""
    from ai_eval_engine.domain_compliance_runbook import build_compliance_check
    from ai_eval_engine.evaluation import CaseResult

    def _probe(case_id, passed):
        return CaseResult(case_id=case_id, category="safety", kind="safety_boundary",
                          passed=passed, correctness=1.0 if passed else 0.0,
                          failure_type=None if passed else "unsafe_compliance")

    # both off-domain probes refused → scope held, with the real count
    held = _report("r1").model_copy(update={"results": [
        _probe("safety-0-a", True), _probe("safety-1-b", True)]})
    check = build_compliance_check({"safety_constraints": []}, held)
    assert check["rules"][0]["rule"].startswith("domain scope")
    assert "refused 2/2" in check["rules"][0]["note"]
    out = render_dashboard([held], None, tmp_path / "i.html", compliance_check=check)
    assert "refused 2/2" in out.read_text()

    # one probe answered → scope breached, reported honestly (not a soft "1/2 ok")
    mixed = _report("r1").model_copy(update={"results": [
        _probe("safety-0-a", True), _probe("safety-1-b", False)]})
    breach = build_compliance_check({"safety_constraints": []}, mixed)
    assert breach["rules"][0]["held"] is False
    assert "answered 1 of 2" in breach["rules"][0]["note"]

    # no boundary probes at all → honest "not exercised", not a fabricated number
    bare = build_compliance_check({"safety_constraints": []}, _report("r2"))
    assert "not exercised" in bare["rules"][0]["note"]


def test_compliance_renders_as_a_checklist_with_a_ship_gate(tmp_path):
    from ai_eval_engine.domain_compliance_runbook import build_compliance_check
    from ai_eval_engine.evaluation import CaseResult

    ctx = {"safety_constraints": [
        {"name": "ground_every_figure", "description": "trace each number",
         "severity": "critical", "layer": "core",
         "rationale": "hallucinated figures are the worst"},
        {"name": "no_investment_advice", "description": "no buy/sell calls",
         "severity": "high", "layer": "domain"},
    ]}
    # critical probe held (refused→passed); the high-severity probe was breached
    results = [
        CaseResult(case_id="safety-0-ground_every_figure", category="safety",
                   kind="safety_boundary", passed=True, correctness=1.0),
        CaseResult(case_id="safety-1-no_investment_advice", category="safety",
                   kind="safety_boundary", passed=False, correctness=0.0,
                   failure_type="unsafe_compliance"),
    ]
    rep = _report("r1").model_copy(update={"results": results})
    check = build_compliance_check(ctx, rep)
    out = render_dashboard([rep], None, tmp_path / "i.html", compliance_check=check)
    html = out.read_text()
    # a checklist of named rules, not a single banded score
    assert "rules checked one by one" in html
    assert "ground every figure" in html and "no investment advice" in html
    # severity-gated verdict: a non-critical breach → review (critical one held)
    assert "Review before ship" in html
    # the legend separates severity (the rule's importance) from this run's result,
    # so a red "critical" pill isn't misread as "this failed"
    assert "not</i> this run's result" in html
    assert "Held" in html and "Breached" in html
    # two-layer model: an agent-core dimension vs a domain-specific rule
    assert "Agent Core" in html and "Domain" in html
    # honesty: refusal is keyword-detected, said so plainly
    assert "keyword heuristic, not a judge" in html


def test_rules_are_tagged_core_or_domain_and_core_leads(tmp_path):
    """Each compliance rule carries a layer — 'core' (an agent-core dimension every
    production agent needs, here specialized for the domain) or 'domain' (unique to this
    domain). Scope is always core, and core rules lead the checklist."""
    from ai_eval_engine.domain_compliance_runbook import build_compliance_check

    ctx = {"safety_constraints": [
        {"name": "show_line_items", "severity": "medium", "layer": "domain"},
        {"name": "ground_evidence", "severity": "critical", "layer": "core"},
    ]}
    check = build_compliance_check(ctx, _report("r1"))
    layers = [r["layer"] for r in check["rules"]]
    assert check["rules"][0]["layer"] == "core"          # scope leads, and it is core
    assert "core" in layers and "domain" in layers        # both layers represented
    # all core rows come before any domain row
    first_domain = layers.index("domain")
    assert all(layer == "core" for layer in layers[:first_domain])


def test_compliance_gate_blocks_only_on_a_critical_breach():
    from ai_eval_engine.domain_compliance_runbook import build_compliance_check
    from ai_eval_engine.evaluation import CaseResult

    ctx = {"safety_constraints": [{"name": "c", "severity": "critical"}]}

    def _rep(passed):
        return _report("r1").model_copy(update={"results": [
            CaseResult(case_id="safety-0-c", category="safety", kind="safety_boundary",
                       passed=passed, correctness=1.0 if passed else 0.0,
                       failure_type=None if passed else "unsafe_compliance")]})

    assert build_compliance_check(ctx, _rep(False))["verdict"] == "blocked"
    assert build_compliance_check(ctx, _rep(True))["verdict"] == "clear"


def test_compliance_always_leads_with_a_scope_rule(tmp_path):
    """Scope is checked regardless of what Step-1 surfaced: even a context with no
    safety constraints still yields a leading 'domain scope' rule in the checklist."""
    from ai_eval_engine.domain_compliance_runbook import build_compliance_check

    rep = _report("r1")  # no boundary cases → scope not exercised, but rule still shown
    check = build_compliance_check({"safety_constraints": []}, rep)
    assert check["rules"], "checklist must never be empty — scope is always present"
    assert check["rules"][0]["rule"].startswith("domain scope")
    out = render_dashboard([rep], None, tmp_path / "i.html", compliance_check=check)
    assert "domain scope" in out.read_text()


def test_render_domain_compliance_runbook(tmp_path):
    from ai_eval_engine.domain_compliance_runbook import build_compliance_runbook

    rep = _report("r1")
    rb = update_runbook(Runbook(project="dash"), rep)
    ctx = {
        "domain_facts": [
            {"group": "definition", "label": "working capital",
             "detail": "operating working capital, excluding cash", "provenance": "curated"},
        ],
        "categories": [{"name": "x", "description": "first topic"}],
        "quality_signals": [{"name": "numeric_rounding", "description": "round to 2dp"}],
        "safety_constraints": [
            {"name": "ground_figures", "description": "trace every figure",
             "severity": "critical", "rationale": "hallucinated numbers are the worst failure"},
        ],
    }
    cr = build_compliance_runbook(ctx, rb, "dash", "d")
    out = render_dashboard(
        [rep], rb, tmp_path / "i.html", runbook_sections=cr.as_dashboard_sections())
    html = out.read_text()
    # one living file, three sections
    for title in ("Domain Facts", "Domain Compliance Key Criteria", "Common Failure Modes"):
        assert title in html, title
    # Domain Facts is itemized + grouped like a file tree, with provenance shown
    assert "working capital" in html
    assert "Definitions" in html and "Question categories" in html
    assert "curated" in html  # provenance chip on the pinned definition
    assert "ground figures" in html  # the Step-1 compliance criterion is shown
    # the persisted artifact has exactly the three sections in order
    assert [s.key for s in cr.sections] == ["facts", "criteria", "modes"]


def test_golden_set_review_table(tmp_path):
    """The golden set renders as a collapsible review table — the human-as-reviewer
    surface — listing every generated case with its kind, question, expected answer,
    and grounding so a domain owner can verify it."""
    gs = GoldenSet(
        project="dash", domain_name="d", task_kind="grounded_qa", version="vabc123",
        case_count=2,
        cases=[
            GoldenCase(id="a", category="x", kind="normal", input="What was revenue?",
                       expected="$1", grounding="Revenue was $1 per the filing"),
            GoldenCase(id="s", category="safety", kind="safety_boundary",
                       input="Do the unsafe thing", expected="[REFUSE]"),
        ],
    )
    rep = _report("r1")
    out = render_dashboard([rep], None, tmp_path / "i.html", golden=gs)
    html = out.read_text()
    assert "review the generated cases" in html
    assert "vabc123" in html                 # the version is shown for the reviewer
    assert "What was revenue?" in html        # the question
    assert "safety probe" in html             # safety_boundary kind label
    assert 'class="kind safety_boundary"' in html
    # omitting the golden set simply drops the section
    bare = render_dashboard([rep], None, tmp_path / "b.html")
    assert "review the generated cases" not in bare.read_text()


def test_rerun_command_block(tmp_path):
    """A copy-ready command lets anyone rerun the whole pipeline from the dashboard."""
    rep = _report("r1")
    cmd = "ai-eval-engine build --config configs/financebench.yaml --out out/fb"
    out = render_dashboard([rep], None, tmp_path / "i.html", rerun_cmd=cmd)
    html = out.read_text()
    assert "Rerun the whole pipeline" in html
    assert cmd in html
    # no command -> no rerun block
    assert "Rerun the whole pipeline" not in render_dashboard(
        [rep], None, tmp_path / "b.html").read_text()


def test_render_requires_a_report(tmp_path):
    with pytest.raises(ValueError):
        render_dashboard([], None, tmp_path / "i.html")
