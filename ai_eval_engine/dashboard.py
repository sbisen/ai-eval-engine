"""Step 5 — Post-Launch Monitoring Dashboard.

Renders a single self-contained ``index.html`` (no external assets, no JS deps)
showing the headline domain metrics, a per-category breakdown, the trend across
runs, and the current safety runbook. Open it in any browser.
"""

from __future__ import annotations

import html
from pathlib import Path

from ai_eval_engine.evaluation import EvalReport
from ai_eval_engine.runbook import Runbook

_CSS = """
:root{--ink:#1b2733;--muted:#5b6b7b;--line:#e3e8ee;--good:#1f9d63;--warn:#b0632f;
--bad:#c0392b;--bg:#f7f9fb}
*{box-sizing:border-box}body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;
margin:0;background:var(--bg);color:var(--ink)}
.wrap{max-width:960px;margin:0 auto;padding:32px 24px 64px}
h1{font-size:24px;margin:0 0 2px}.sub{color:var(--muted);margin:0 0 24px;font-size:14px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:28px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px}
.card .v{font-size:28px;font-weight:700}.card .l{color:var(--muted);font-size:12px;
text-transform:uppercase;letter-spacing:.04em;margin-top:4px}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);
margin:28px 0 10px}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);
border-radius:12px;overflow:hidden;font-size:14px}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line)}
th{background:#fbfcfd;color:var(--muted);font-weight:600;font-size:12px;
text-transform:uppercase;letter-spacing:.03em}tr:last-child td{border-bottom:0}
.bar{height:8px;background:var(--line);border-radius:5px;overflow:hidden;min-width:80px}
.bar>span{display:block;height:100%;background:var(--good)}
.pill{display:inline-block;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:600}
.critical{background:#fdecea;color:var(--bad)}.high{background:#fdf0e7;color:var(--warn)}
.medium{background:#fff6e0;color:#9a7a14}.low{background:#eef2f6;color:var(--muted)}
.trend{display:flex;gap:6px;align-items:flex-end;height:90px;background:#fff;
border:1px solid var(--line);border-radius:12px;padding:14px}
.trend .b{flex:1;background:var(--good);border-radius:4px 4px 0 0;min-width:14px;position:relative}
.trend .b span{position:absolute;bottom:-18px;left:0;right:0;text-align:center;
font-size:10px;color:var(--muted)}
.foot{color:var(--muted);font-size:12px;margin-top:28px}
.empty{color:var(--muted);font-style:italic;padding:14px}
"""


def _e(s: object) -> str:
    return html.escape(str(s))


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{round(x * 100)}%"


def _color(x: float) -> str:
    return "var(--good)" if x >= 0.8 else "var(--warn)" if x >= 0.5 else "var(--bad)"


def render_dashboard(
    reports: list[EvalReport], runbook: Runbook | None, out_path: str | Path
) -> Path:
    """Write index.html. ``reports`` is run history (oldest→newest); last is current."""
    if not reports:
        raise ValueError("render_dashboard needs at least one EvalReport")
    cur = reports[-1]

    cards = "".join(
        f'<div class="card"><div class="v" style="color:{_color(v)}">{_pct(v)}</div>'
        f'<div class="l">{lab}</div></div>'
        for lab, v in [
            ("Domain Accuracy", cur.domain_accuracy),
            ("Pass Rate", cur.pass_rate),
            ("Safety Score", cur.safety_score),
            ("Grounding", cur.grounding_rate if cur.grounding_rate is not None else 1.0),
        ]
    )

    cat_rows = "".join(
        f"<tr><td>{_e(cat)}</td><td>{int(m['n'])}</td>"
        f"<td>{_pct(m['accuracy'])}</td>"
        f'<td><div class="bar"><span style="width:{round(m["pass_rate"]*100)}%;'
        f'background:{_color(m["pass_rate"])}"></span></div></td></tr>'
        for cat, m in cur.by_category.items()
    ) or '<tr><td colspan="4" class="empty">no categories</td></tr>'

    items = runbook.items if runbook else []
    rb_rows = "".join(
        f'<tr><td><span class="pill {_e(it.severity)}">{_e(it.severity)}</span></td>'
        f"<td>{_e(it.title)}</td><td>{it.occurrences}</td><td>{_e(it.status)}</td>"
        f"<td>{_e(it.recommended_check)}</td></tr>"
        for it in items
    ) or '<tr><td colspan="5" class="empty">no failures recorded — clean run</td></tr>'

    mx = max((r.pass_rate for r in reports), default=1.0) or 1.0
    trend = "".join(
        f'<div class="b" style="height:{max(6, round(r.pass_rate/mx*100))}%;'
        f'background:{_color(r.pass_rate)}" title="{_e(r.run_id)}: {_pct(r.pass_rate)}">'
        f"<span>{_pct(r.pass_rate)}</span></div>"
        for r in reports[-12:]
    )

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_e(cur.project)} — Eval Dashboard</title><style>{_CSS}</style></head><body>
<div class="wrap">
<h1>{_e(cur.project)}</h1>
<p class="sub">Domain-aware eval · task type <b>{_e(cur.task_kind)}</b> ·
run <b>{_e(cur.run_id)}</b> · {cur.n} cases · {len(reports)} run(s)</p>
<div class="cards">{cards}</div>
<h2>Pass rate by run</h2><div class="trend">{trend}</div>
<h2>By domain / category</h2>
<table><tr><th>Category</th><th>Cases</th><th>Accuracy</th><th>Pass rate</th></tr>{cat_rows}</table>
<h2>Safety runbook ({len(items)} item{'s' if len(items)!=1 else ''})</h2>
<table><tr><th>Severity</th><th>Pattern</th><th>Count</th><th>Status</th>
<th>Recommended check</th></tr>{rb_rows}</table>
<p class="foot">Generated by AI Eval Engine. Self-contained — no network calls.</p>
</div></body></html>"""

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc)
    return out
