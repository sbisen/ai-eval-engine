"""Step 5 — Post-Launch Monitoring Dashboard.

Renders a single self-contained ``index.html`` (no external assets, no JS deps)
showing the headline domain metrics, a per-category breakdown, and the
Domain-Compliance Runbook (Facts · Criteria · Failure Modes). Open it in any browser.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import TYPE_CHECKING

from ai_eval_engine.evaluation import EvalReport
from ai_eval_engine.eval_learnings import Runbook

if TYPE_CHECKING:
    from ai_eval_engine.golden_set import GoldenSet

_CSS = """
:root{--ink:#1b2733;--muted:#5b6b7b;--line:#e3e8ee;--good:#1f9d63;--warn:#b0632f;
--bad:#c0392b;--bg:#f7f9fb}
*{box-sizing:border-box}body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;
margin:0;background:var(--bg);color:var(--ink)}
.wrap{max-width:960px;margin:0 auto;padding:32px 24px 64px}
h1{font-size:24px;margin:0 0 2px}.sub{color:var(--muted);margin:0 0 24px;font-size:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
gap:14px;margin-bottom:28px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px}
.card.north{border-color:var(--good);box-shadow:0 0 0 1px var(--good) inset}
.card .v{font-size:28px;font-weight:700}.card .l{color:var(--muted);font-size:12px;
text-transform:uppercase;letter-spacing:.04em;margin-top:4px}
.card .pr{color:var(--muted);font-size:11px;margin-top:2px}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);
margin:28px 0 10px}
.fold{margin:0}
.fold>summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:8px}
.fold>summary::-webkit-details-marker{display:none}
.fold>summary>h2{margin:28px 0 10px}
.fold>summary::before{content:"▸";color:var(--muted);font-size:12px;margin-top:18px;
transition:transform .12s}
.fold[open]>summary::before{transform:rotate(90deg)}
.flow{display:flex;flex-wrap:nowrap;align-items:stretch;gap:6px;margin:10px 0 28px;width:100%}
.fstep{flex:1 1 0;min-width:0;display:flex;align-items:center;gap:7px;background:#fff;
border:1px solid var(--line);border-radius:10px;padding:9px 11px;font-size:12px;
font-weight:600;color:var(--ink);line-height:1.25}
.fstep.done{border-color:#cfe6d6;background:#f3faf5}
.fstep .fnum{flex:0 0 20px;height:20px;border-radius:50%;display:flex;align-items:center;
justify-content:center;font-size:11px;font-weight:700;background:var(--muted);color:#fff}
.fstep.done .fnum{background:#2f7d4f}
.fstep .flabel{min-width:0}
.farrow{flex:0 0 auto;color:var(--muted);font-size:13px;align-self:center}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);
border-radius:12px;overflow:hidden;font-size:14px}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line)}
th{background:#fbfcfd;color:var(--muted);font-weight:600;font-size:12px;
text-transform:uppercase;letter-spacing:.03em}tr:last-child td{border-bottom:0}
.pill{display:inline-block;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:600}
.critical{background:#fdecea;color:var(--bad)}.high{background:#fdf0e7;color:var(--warn)}
.medium{background:#fff6e0;color:#9a7a14}.low{background:#eef2f6;color:var(--muted)}
.foot{color:var(--muted);font-size:12px;margin-top:28px}
.empty{color:var(--muted);font-style:italic;padding:14px}
.rb{background:#fff;border:1px solid var(--line);border-radius:12px;padding:2px 16px}
.sec{padding:16px 0;border-top:1px solid var(--line)}
.sec:first-child{border-top:0}
.sec h3{margin:0;font-size:14px;display:flex;align-items:center;gap:8px}
.sec .num{flex:0 0 22px;height:22px;border-radius:6px;background:var(--ink);color:#fff;
font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center}
.sec .ssum{color:var(--muted);font-size:12px;margin:3px 0 10px 30px}
.sec .grp{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);
font-weight:700;margin:12px 0 0;padding-top:8px;border-top:1px solid var(--line)}
.sec .grp:first-of-type{border-top:0;padding-top:0}
.sec ul{list-style:none;margin:0;padding:0}
.sec li{padding:8px 0;border-top:1px solid var(--line);font-size:13px}
.sec li:first-child{border-top:0}
.sec .rl{font-weight:600;display:flex;align-items:center;gap:8px}
.sec .rd{color:var(--muted);font-size:12px;margin-top:2px;line-height:1.45}
.count{background:#eef2f6;color:var(--muted);border-radius:20px;padding:1px 8px;
font-size:11px;font-weight:700}
.gate{font-weight:700;font-size:14px;padding:12px 16px;border-radius:12px;margin:0 0 12px;
border:1px solid var(--line)}
.gate.clear{background:#eaf7ef;color:var(--good);border-color:#bfe6cf}
.gate.review{background:#fdf3e8;color:var(--warn);border-color:#f1d6b8}
.gate.blocked{background:#fdecea;color:var(--bad);border-color:#f3c6c0}
td.gi{font-weight:700;text-align:center;width:28px}
td.gi.ok{color:var(--good)}td.gi.bad{color:var(--bad)}td.gi.na{color:var(--muted)}
td.gn{color:var(--muted);font-size:13px}
.sev{display:inline-block;padding:2px 9px;border-radius:20px;font-size:12px;
font-weight:600;background:#eef2f6;color:var(--muted)}
.lay{display:inline-block;padding:1px 8px;border-radius:20px;font-size:10px;
font-weight:700;text-transform:uppercase;letter-spacing:.03em;vertical-align:middle}
.lay.core{background:#e8f0fe;color:#2c5fb3}.lay.domain{background:#eef7f0;color:#2f7d4f}
.st{font-weight:700;margin-right:4px}
.st.ok{color:var(--good)}.st.bad{color:var(--bad)}.st.na{color:var(--muted)}
.legend{color:var(--muted);font-size:12px;line-height:1.5;margin:0 0 12px;max-width:780px}
.rerun{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px;
margin:0 0 28px}
.rerun .rrl{font-weight:700;font-size:14px}
.rerun .rrh{color:var(--muted);font-size:12px;margin:3px 0 10px}
.rerun pre.cmd{margin:0;background:#0f1b27;color:#e6edf3;border-radius:8px;padding:10px 12px;
font-size:12.5px;overflow-x:auto;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.kind{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:600;
white-space:nowrap}
.kind.normal{background:#eef2f6;color:var(--muted)}
.kind.ambiguous{background:#fff6e0;color:#9a7a14}
.kind.out_of_scope{background:#fdf0e7;color:var(--warn)}
.kind.safety_boundary{background:#e8f0fe;color:#2c5fb3}
td.gnd{color:var(--muted);font-size:12px;max-width:280px}
"""


def _runbook_sections_html(sections: list[dict]) -> str:
    """Render the Domain-Compliance Runbook. Each section's rows are grouped by their
    optional ``group`` key into filesystem-like sub-folders (e.g. Definitions,
    Question categories, Data characteristics)."""
    blocks = []
    for i, s in enumerate(sections, 1):
        body, last_group = [], None
        for r in s["rows"]:
            grp = r.get("group") or ""
            if grp != last_group:
                if last_group is not None:
                    body.append("</ul>")
                if grp:
                    body.append(f'<div class="grp">{_e(grp)}</div>')
                body.append("<ul>")
                last_group = grp
            tag = (f'<span class="pill {_e(r["tag"])}">{_e(r["tag"])}</span>'
                   if r.get("tag") else "")
            cnt = f'<span class="count">{_e(r["count"])}</span>' if r.get("count") else ""
            body.append(
                f'<li><div class="rl">{_e(r["label"])}{tag}{cnt}</div>'
                f'<div class="rd">{_e(r["detail"])}</div></li>'
            )
        if last_group is None:
            inner = '<ul><li class="rd">none recorded — clean run</li></ul>'
        else:
            body.append("</ul>")
            inner = "".join(body)
        blocks.append(
            f'<div class="sec"><h3><span class="num">{i}</span>{_e(s["title"])}</h3>'
            f'<div class="ssum">{_e(s["summary"])}</div>{inner}</div>'
        )
    return f'<div class="rb">{"".join(blocks)}</div>'


_FLOW_STEPS = (
    "Domain Context Ingestion",
    "Generate Domain-Compliance Runbook",
    "Generate Golden-set",
    "Run AI Evals",
    "Score Dashboard UI",
)


def _steps_html() -> str:
    """Horizontal pipeline flowchart. A dashboard exists only after a full build,
    so every step shows a ✓ (done)."""
    cells = []
    for i, label in enumerate(_FLOW_STEPS, 1):
        if i > 1:
            cells.append('<div class="farrow">&rarr;</div>')
        cells.append(
            f'<div class="fstep done"><span class="fnum">✓</span>'
            f'<span class="flabel">{i}. {_e(label)}</span></div>'
        )
    return '<h2>Pipeline</h2><div class="flow">' + "".join(cells) + "</div>"


def _rerun_html(cmd: str | None) -> str:
    """A copy-ready command to regenerate the whole bundle. The dashboard is static,
    so "rerun" means: run this one line in a terminal and every artifact above is
    rebuilt — golden set, scores, runbook, and this page (the trend grows each run)."""
    if not cmd:
        return ""
    return (
        '<div class="rerun"><div class="rrl">&#x21bb; Rerun the whole pipeline</div>'
        '<div class="rrh">Regenerates Steps 1&ndash;5 and this dashboard. '
        'Each run appends to the trend and grows the runbook.</div>'
        f'<pre class="cmd">{_e(cmd)}</pre></div>'
    )


_KIND_LABEL = {
    "normal": "normal",
    "ambiguous": "ambiguous",
    "out_of_scope": "out of scope",
    "safety_boundary": "safety probe",
}


def _clip(s: object, n: int = 200) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _golden_html(golden: "GoldenSet | None") -> str:
    """Collapsible 'review the golden set' table — the human-as-reviewer surface.

    Every generated case is listed so a domain owner can verify it without trusting the
    generator: its kind, category, the question posed, the expected answer, and the
    grounding that backs it. Grounding is clipped for scanability (full text on hover and
    in ``golden_set.json``)."""
    if golden is None or not getattr(golden, "cases", None):
        return ""
    rows = []
    for i, c in enumerate(golden.cases, 1):
        kind = getattr(c, "kind", "normal")
        grounding = getattr(c, "grounding", None) or ""
        gcell = (
            f'<td class="gnd" title="{_e(grounding)}">{_e(_clip(grounding, 160))}</td>'
            if grounding else '<td class="gnd">&mdash;</td>'
        )
        rows.append(
            f'<tr><td class="gn">{i}</td>'
            f'<td><span class="kind {_e(kind)}">{_e(_KIND_LABEL.get(kind, kind))}</span></td>'
            f"<td>{_e(c.category)}</td><td>{_e(c.input)}</td>"
            f"<td>{_e(c.expected)}</td>{gcell}</tr>"
        )
    summary = (
        f"{golden.case_count} cases &middot; version <code>{_e(golden.version)}</code> "
        "&middot; you are the reviewer &mdash; verify each generated case is right for the domain"
    )
    return (
        '<details class="fold"><summary><h2>Golden Set &mdash; review the generated cases'
        "</h2></summary>"
        f'<p class="legend">{summary}</p>'
        "<table><tr><th>#</th><th>Kind</th><th>Category</th><th>Question</th>"
        f"<th>Expected answer</th><th>Grounding</th></tr>{''.join(rows)}</table></details>"
    )


def _e(s: object) -> str:
    return html.escape(str(s))


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{round(x * 100)}%"


def _color(x: float) -> str:
    return "var(--good)" if x >= 0.8 else "var(--warn)" if x >= 0.5 else "var(--bad)"


def _okr_cards(report: EvalReport) -> str:
    """Render the two scalar Step-5 OKR cards: **Domain Accuracy** and
    **Avg Confidence**.

    Scope is *not* a card — it leads the Compliance checklist (row 1, always present),
    so a separate Scope Safeguard card would just duplicate it. Compliance as a whole is
    a per-rule checklist with a ship-gate verdict (see :func:`_compliance_html`), not a
    single banded number.
    """
    # 1 — Domain Accuracy: avg correctness over the real answers.
    da = report.domain_accuracy
    cards = [
        '<div class="card north">'
        f'<div class="v" style="color:{_color(da)}">{_pct(da)}</div>'
        '<div class="l">Domain Accuracy</div>'
        '<div class="pr">avg correctness across answers</div></div>'
    ]

    # 2 — Avg Confidence: per-row match score between the answer and the grounded
    #     evidence, averaged. (Evidence-match confidence, not an LLM self-report.)
    conf = report.grounding_rate
    conf_v = _pct(conf) if conf is not None else "—"
    conf_color = _color(conf) if conf is not None else "var(--muted)"
    cards.append(
        f'<div class="card"><div class="v" style="color:{conf_color}">{conf_v}</div>'
        '<div class="l">Avg Confidence Score</div>'
        '<div class="pr">answer ↔ evidence match, per row</div></div>'
    )
    return "".join(cards)


_GATE_ICON = {True: "✓", False: "⚠", None: "·"}
_GATE_CLASS = {True: "ok", False: "bad", None: "na"}
_GATE_LABEL = {True: "Held", False: "Breached", None: "Not run"}
_LAYER_LABEL = {"core": "Agent Core", "domain": "Domain"}


def _note_tail(note: str) -> str:
    """Strip a leading 'held — ' / 'breached — ' / 'not …' status word from a rule note,
    so the rendered status pill (Held / Breached / Not run) isn't duplicated in prose."""
    s = str(note or "")
    low = s.lower()
    for lead in ("held — ", "held - ", "breached — ", "breached - "):
        if low.startswith(lead):
            return s[len(lead):]
    if low.startswith("not "):  # "not exercised …" / "not run this run"
        return ""
    return s


def _compliance_html(check: dict | None) -> str:
    """Render Compliance as a **checklist of named domain rules with a ship-gate
    verdict** — not a single score. ``check`` comes from
    :func:`ai_eval_engine.domain_compliance_runbook.build_compliance_check`.

    Each row is a real Step-1 safety rule and whether its boundary probe held this
    run; the verdict is severity-gated (a critical breach blocks the ship). Returns an
    empty string when no compliance check is available (e.g. a domain with no rules).
    """
    if not check or not check.get("rules"):
        return ""
    rows = "".join(
        f'<tr><td class="gi {_GATE_CLASS[r["held"]]}">{_GATE_ICON[r["held"]]}</td>'
        f'<td>{_e(r["rule"])} '
        f'<span class="lay {_e(r.get("layer", "domain"))}">'
        f'{_LAYER_LABEL.get(r.get("layer", "domain"), "Domain")}</span></td>'
        f'<td><span class="sev">{_e(r["severity"])}</span></td>'
        f'<td class="gn"><span class="st {_GATE_CLASS[r["held"]]}">'
        f'{_GATE_LABEL[r["held"]]}</span> {_e(_note_tail(r["note"]))}</td></tr>'
        for r in check["rules"]
    )
    foot = (
        f'<p class="foot">{_e(check["other_note"])} '
        if check.get("other_note") else '<p class="foot">'
    )
    foot += "Refusal is detected by a keyword heuristic, not a judge model.</p>"
    return (
        '<h2>Compliance — rules checked one by one</h2>'
        '<p class="legend"><b>Agent Core</b> = compliance every production agent needs '
        '(scope, grounding, no-bias, escalation), here specialized for this domain. '
        '<b>Domain</b> = a rule unique to this domain, surfaced from its data. '
        '<b>Importance</b> is how serious a breach would be — the rule\'s standing, '
        "<i>not</i> this run's result. The ✓ / ⚠ icon and the <b>Result</b> "
        'column are the outcome: <b>✓ Held</b> = the agent did the right thing; '
        '<b>⚠ Breached</b> = it did not.</p>'
        f'<div class="gate {_e(check["verdict"])}">{_e(check["label"])}</div>'
        '<table><tr><th></th><th>Compliance rule</th><th>Importance</th>'
        f'<th>Result</th></tr>{rows}</table>{foot}'
    )


def render_dashboard(
    reports: list[EvalReport],
    runbook: Runbook | None,
    out_path: str | Path,
    runbook_sections: list[dict] | None = None,
    compliance_check: dict | None = None,
    golden: "GoldenSet | None" = None,
    rerun_cmd: str | None = None,
) -> Path:
    """Write index.html. ``reports`` is run history (oldest→newest); last is current.

    ``runbook_sections`` (from
    :meth:`ai_eval_engine.domain_compliance_runbook.DomainComplianceRunbook.as_dashboard_sections`)
    renders the Domain-Compliance Runbook — Facts · Criteria · Failure Modes, grouped
    like a file tree — instead of a flat item table.
    ``compliance_check`` (from
    :func:`ai_eval_engine.domain_compliance_runbook.build_compliance_check`) renders the
    Compliance block as a per-rule checklist with a severity-gated ship verdict —
    *not* a single banded score.
    The Step-5 OKR cards are a **fixed two** — Domain Accuracy and Avg Confidence Score —
    with Compliance shown as the checklist below.
    ``golden`` (the Step-2 :class:`GoldenSet`) renders a collapsible *review* table so a
    domain owner can verify every generated case. ``rerun_cmd`` is a copy-ready command
    that regenerates the whole bundle (the page is static, so rerunning is a terminal
    one-liner, not a button).
    """
    if not reports:
        raise ValueError("render_dashboard needs at least one EvalReport")
    cur = reports[-1]

    cards = _okr_cards(cur)

    items = runbook.items if runbook else []
    rb_rows = "".join(
        f'<tr><td><span class="pill {_e(it.severity)}">{_e(it.severity)}</span></td>'
        f"<td>{_e(it.title)}</td><td>{it.occurrences}</td><td>{_e(it.status)}</td>"
        f"<td>{_e(it.recommended_check)}</td></tr>"
        for it in items
    ) or '<tr><td colspan="5" class="empty">no failures recorded — clean run</td></tr>'

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_e(cur.project)} — Eval Dashboard</title><style>{_CSS}</style></head><body>
<div class="wrap">
<h1>{_e(cur.project)}</h1>
<p class="sub">Domain-aware eval · task type <b>{_e(cur.task_kind)}</b> ·
run <b>{_e(cur.run_id)}</b> · {cur.n} cases · {len(reports)} run(s)</p>
{_steps_html()}
{_rerun_html(rerun_cmd)}
<details class="fold" open><summary><h2>Domain-Compliance Runbook</h2></summary>
{_runbook_sections_html(runbook_sections) if runbook_sections else
 f'<table><tr><th>Severity</th><th>Pattern</th><th>Count</th><th>Status</th>'
 f'<th>Recommended check</th></tr>{rb_rows}</table>'}
</details>
{_golden_html(golden)}
<h2>AI Eval Dashboard</h2>
<div class="cards">{cards}</div>
{_compliance_html(compliance_check)}
<p class="foot">Generated by AI Eval Engine. Self-contained — no network calls.</p>
</div></body></html>"""

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc)
    return out
