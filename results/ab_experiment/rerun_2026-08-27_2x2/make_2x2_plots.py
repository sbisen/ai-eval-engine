"""Figures for the 2x2 factorial rerun (documents x runbook), k runs per cell.
Reads cell_*/run*/golden_set_*.json; writes into THIS folder only:
  domain_accuracy_results.json / domain_accuracy_chart.html   (2x2 grouped bars, mean +- sd over runs)
  relatedness_results.json     / relatedness_boxplot.html     (4 boxes, questions pooled over runs)
  bubble_results.json          / bubble_chart.html            (run1 per cell; hand-verified topics if present)
  golden_set_question_types.html                              (4 panels, run1 per cell)
  coverage_table.html                                         (4 columns, mean +- sd over runs)
  topic_model_assignments.auto.json
Scorer is rule-based and identical for every cell (see score()); it is NOT an LLM judge.
"""
from __future__ import annotations
import json, re, glob
from pathlib import Path
import numpy as np
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rerun_2026-08-27"))
# --- import the shared pieces explicitly (make_rerun_plots defines them at module level)
import importlib.util
_spec = importlib.util.spec_from_file_location("mrp", Path(__file__).resolve().parent.parent / "rerun_2026-08-27" / "make_rerun_plots.py")
mrp = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(mrp)
score, relatedness, specificity, stats, figure_verifiable, auto_topics, shell, DECLINE, PROBE = (
    mrp.score, mrp.relatedness, mrp.specificity, mrp.stats, mrp.figure_verifiable, mrp.auto_topics, mrp.shell, mrp.DECLINE, mrp.PROBE)

HERE = Path(__file__).resolve().parent
CELLS = [  # key, docs, runbook, label, color, dir
    ("00", False, False, "no documents · no runbook",  "#9aa3ad", "cell_00_blind"),
    ("10", False, True,  "no documents · runbook",     "#c98a3a", "cell_10_runbook"),
    ("01", True,  False, "documents · no runbook",     "#5aa47a", "cell_01_docs"),
    ("11", True,  True,  "documents · runbook",        "#3f6fb0", "cell_11_docs_runbook"),
]
CRITERIA = ["Domain scope", "Citation & non-misleading disclosure", "MNPI & confidential-information safeguard",
            "No personal bias / no advice", "Escalate to Human"]

def load_runs(d):
    runs = []
    for p in sorted(glob.glob(str(HERE / d / "run*" / "golden_set_*.json"))):
        cases = json.loads(Path(p).read_text())["cases"]
        runs.append(dict(path=p, cases=cases, cap=[c for c in cases if c.get("question_type") != PROBE],
                         cmp=[c for c in cases if c.get("question_type") == PROBE]))
    return runs

def msd(vals):
    v = np.array(vals, float)
    return float(v.mean()), (float(v.std(ddof=1)) if len(v) > 1 else 0.0)

def main():
    cells = {}
    for key, docs, rb, label, color, d in CELLS:
        runs = load_runs(d)
        cells[key] = dict(docs=docs, rb=rb, label=label, color=color, runs=runs)
        print(f"cell {key} {label}: {len(runs)} runs")
    active = {k: v for k, v in cells.items() if v["runs"]}

    # ---------------- domain accuracy: per run, then mean +- sd
    da = {}
    for k, c in active.items():
        per_run = []
        rows_all = []
        for i, r in enumerate(c["runs"], 1):
            rows = [{"run": i, "id": x["id"], "company": x.get("company") or "", "question": x["input"], **dict(zip(("score", "reason"), score(x)))} for x in r["cap"]]
            per_run.append(sum(x["score"] for x in rows) / len(rows)); rows_all += rows
        m, sd = msd(per_run)
        da[k] = dict(per_run=[round(x, 4) for x in per_run], mean=round(m, 4), sd=round(sd, 4), n_runs=len(per_run), rows=rows_all)
    summary = {"metric": "graded question domain accuracy = mean(relevance, groundedness vs raw FinanceBench JSON); questions, not answers; compliance probes excluded",
               "scorer": "rule-based (rerun_2026-08-27/make_rerun_plots.py::score), identical for all cells — NOT an LLM judge",
               "design": "2x2 factorial: documents (filing evidence text only, no benchmark Q&A) x runbook; k runs per cell",
               **{f"cell_{k}": {kk: vv for kk, vv in v.items() if kk != "rows"} | {"label": active[k]["label"]} for k, v in da.items()}}
    (HERE / "domain_accuracy_results.json").write_text(json.dumps({"summary": summary, **{f"cell_{k}": v["rows"] for k, v in da.items()}}, indent=2))
    print(json.dumps({k: {"mean": v["mean"], "sd": v["sd"], "runs": v["per_run"]} for k, v in da.items()}, indent=1))

    # chart: two groups (documents no / yes), two bars each (runbook no / yes)
    L, R, T, B = 150, 1180, 110, 560; h = B - T
    def y(p): return B - h * p / 100
    grid = "".join(f'<line x1="{L}" y1="{y(p):.1f}" x2="{R}" y2="{y(p):.1f}" stroke="#e5e7eb"/><text x="{L-18}" y="{y(p)+6:.1f}" text-anchor="end" font-size="26" fill="#6b7280">{p}%</text>' for p in range(0, 101, 20))
    bars = ""; bw = 190
    groups = [("No documents", ["00", "10"], 420), ("Documents (filing text)", ["01", "11"], 910)]
    for gl, keys, gx in groups:
        for j, k in enumerate(keys):
            if k not in da: continue
            cx = gx + (j - 0.5) * (bw + 30); pct = 100 * da[k]["mean"]; sd = 100 * da[k]["sd"]; top = y(pct); col = active[k]["color"]
            bars += (f'<rect x="{cx-bw/2:.0f}" y="{top:.1f}" width="{bw}" height="{B-top:.1f}" rx="4" fill="{col}"/>'
                     f'<line x1="{cx}" y1="{y(pct+sd):.1f}" x2="{cx}" y2="{y(max(0,pct-sd)):.1f}" stroke="#111827" stroke-width="3"/>'
                     f'<line x1="{cx-18}" y1="{y(pct+sd):.1f}" x2="{cx+18}" y2="{y(pct+sd):.1f}" stroke="#111827" stroke-width="3"/>'
                     f'<line x1="{cx-18}" y1="{y(max(0,pct-sd)):.1f}" x2="{cx+18}" y2="{y(max(0,pct-sd)):.1f}" stroke="#111827" stroke-width="3"/>'
                     f'<text x="{cx}" y="{y(pct+sd)-14:.1f}" text-anchor="middle" font-size="32" font-weight="700" fill="#1f2937">{pct:.0f}%</text>'
                     f'<text x="{cx}" y="{B+34}" text-anchor="middle" font-size="21" fill="#374151">{"runbook" if active[k]["rb"] else "no runbook"}</text>')
        bars += f'<text x="{gx}" y="{B+74}" text-anchor="middle" font-size="26" font-weight="700" fill="#111827">{gl}</text>'
    svg = f'<svg viewBox="0 0 1280 680" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Segoe UI,Roboto,sans-serif"><rect width="1280" height="680" fill="#fff"/>{grid}<line x1="{L}" y1="{T}" x2="{L}" y2="{B}" stroke="#d1d5db"/><line x1="{L}" y1="{B}" x2="{R}" y2="{B}" stroke="#d1d5db"/>{bars}<text x="{(L+R)/2:.0f}" y="70" text-anchor="middle" font-size="24" fill="#6b7280">mean ± sd over k = {max(v["n_runs"] for v in da.values())} generation runs per cell · rule-based scorer, identical for every cell</text></svg>'
    def g(k): return f"{100*da[k]['mean']:.0f}%" if k in da else "–"
    foot = (f"2 × 2 factorial: <b>documents</b> (filing evidence text only — the benchmark's own questions and answers were removed, so no cell can paraphrase them) × "
            f"<b>runbook</b> (the extracted Domain Compliance Runbook). Groundedness is verified against the raw filing data, so it is primarily a <i>documents</i> effect: "
            f"{g('00')} → {g('01')} without the runbook, {g('10')} → {g('11')} with it. The runbook's contribution appears on the other axes (coverage table, specificity), not here. "
            f"Compliance probes excluded from this metric. Rerun 2026-08-27.")
    (HERE / "domain_accuracy_chart.html").write_text(shell("Domain accuracy of generated questions &mdash; documents &times; runbook", "FinanceBench golden sets &middot; 2 &times; 2 factorial rerun 2026-08-27 &middot; we test the questions, not the answers", svg, foot, 1040))

    # ---------------- relatedness: questions pooled across runs
    rel = {k: [{"run": i, "id": x["id"], "score": round(v, 4), "question": x["input"]} for i, r in enumerate(c["runs"], 1) for x, v in zip(r["cap"], relatedness(r["cap"]))] for k, c in active.items()}
    st = {k: stats([r["score"] for r in rel[k]]) for k in rel}
    ymax = round(max(s["max"] for s in st.values()) * 1.15 + 0.005, 2)
    L, R, T, B = 180, 1180, 90, 540; h = B - T
    def yy(v): return B - h * v / ymax
    grid = "".join(f'<line x1="{L}" y1="{yy(t):.1f}" x2="{R}" y2="{yy(t):.1f}" stroke="#e5e7eb"/><text x="{L-16}" y="{yy(t)+6:.1f}" text-anchor="end" font-size="26" fill="#6b7280">{t:.2f}</text>' for t in np.linspace(0, ymax, 6))
    body = ""; boxw = 170
    for (k, c), cx in zip(active.items(), [300, 540, 780, 1020]):
        s = st[k]; col = c["color"]; vals = sorted(r["score"] for r in rel[k])
        body += f'<line x1="{cx}" y1="{yy(s["max"]):.1f}" x2="{cx}" y2="{yy(s["min"]):.1f}" stroke="{col}" stroke-width="2"/>'
        for cap in (s["max"], s["min"]): body += f'<line x1="{cx-36}" y1="{yy(cap):.1f}" x2="{cx+36}" y2="{yy(cap):.1f}" stroke="{col}" stroke-width="2"/>'
        body += f'<rect x="{cx-boxw/2:.0f}" y="{yy(s["q3"]):.1f}" width="{boxw}" height="{abs(yy(s["q1"])-yy(s["q3"])):.1f}" rx="3" fill="{col}" fill-opacity="0.18" stroke="{col}" stroke-width="2.5"/>'
        body += f'<line x1="{cx-boxw/2:.0f}" y1="{yy(s["median"]):.1f}" x2="{cx+boxw/2:.0f}" y2="{yy(s["median"]):.1f}" stroke="{col}" stroke-width="3.5"/>'
        for i, v in enumerate(vals): body += f'<circle cx="{cx+((i*53)%100/100-0.5)*(boxw-40):.1f}" cy="{yy(v):.1f}" r="3.5" fill="{col}" fill-opacity="0.45"/>'
        body += f'<circle cx="{cx}" cy="{yy(s["mean"]):.1f}" r="7" fill="#fff" stroke="{col}" stroke-width="3"/>'
        l1, l2 = c["label"].split(" · ")
        body += f'<text x="{cx}" y="{B+34}" text-anchor="middle" font-size="22" font-weight="700" fill="#111827">{l1}</text><text x="{cx}" y="{B+60}" text-anchor="middle" font-size="22" font-weight="700" fill="#111827">{l2}</text>'
        body += f'<text x="{cx}" y="{B+86}" text-anchor="middle" font-size="18" fill="#6b7280">median {s["median"]:.3f} · mean {s["mean"]:.3f} · n={s["n"]}</text>'
    svg = f'<svg viewBox="0 0 1280 660" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Segoe UI,Roboto,sans-serif"><rect width="1280" height="660" fill="#fff"/><text x="44" y="{(T+B)/2:.0f}" transform="rotate(-90 44 {(T+B)/2:.0f})" text-anchor="middle" font-size="24" fill="#374151">Domain relatedness (max TF-IDF cosine)</text>{grid}<line x1="{L}" y1="{T}" x2="{L}" y2="{B}" stroke="#d1d5db"/><line x1="{L}" y1="{B}" x2="{R}" y2="{B}" stroke="#d1d5db"/>{body}</svg>'
    foot = ("Max TF-IDF cosine of each generated question to the closest real FinanceBench record (question + answer + evidence); questions pooled over all runs of a cell; compliance probes excluded. "
            "Box = IQR, line = median, hollow dot = mean. Offline and reproducible. 2 × 2 factorial rerun 2026-08-27.")
    (HERE / "relatedness_boxplot.html").write_text(shell("Per-question domain relatedness &mdash; documents &times; runbook", "FinanceBench golden sets &middot; 2 &times; 2 factorial rerun 2026-08-27 &middot; distribution over the questions (not answers)", svg, foot, 1040))
    (HERE / "relatedness_results.json").write_text(json.dumps({**{f"cell_{k}_stats": st[k] for k in st}, **{f"cell_{k}": rel[k] for k in rel}}, indent=2))

    # ---------------- topics on run1 of each cell
    hand = HERE / "topic_model_assignments.json"
    handd = json.loads(hand.read_text()) if hand.exists() else {}
    def topics_for(k, cases):
        if k in handd:
            d = handd[k]; out = [(t, "cap", d["assignments"][t]) for t in d["capability_subtree_topics"]]
            return out + [(t, "cmp", d["assignments"][t]) for t in d.get("compliance_subtree_topics", [])]
        cap = [c for c in cases if c.get("question_type") != PROBE]; cmp = [c for c in cases if c.get("question_type") == PROBE]
        out = [(t, "cap", ids) for t, ids in auto_topics(cap, 6).items()]
        by = {}
        for c in cmp: by.setdefault((c.get("probes_criteria") or ["(untagged)"])[0], []).append(c["id"])
        return out + [(t, "cmp", ids) for t, ids in by.items()]
    auto = {k: {"capability": auto_topics(c["runs"][0]["cap"], 6), "compliance": {t: ids for t, kd, ids in topics_for(k, c["runs"][0]["cases"]) if kd == "cmp"}} for k, c in active.items()}
    (HERE / "topic_model_assignments.auto.json").write_text(json.dumps(auto, indent=2))
    src = "hand-verified topic_model_assignments.json" if handd else "automatic NMF topics (top-3 terms; not yet hand-verified)"
    allc = {x["id"] + "@" + k: x for k, c in active.items() for x in c["runs"][0]["cases"]}
    relall = {x["id"] + "@" + k: v for k, c in active.items() for x, v in zip(c["runs"][0]["cases"], relatedness(c["runs"][0]["cases"]))}
    spec = {i: specificity(x) for i, x in allc.items()}
    bubbles = []
    for k, c in active.items():
        for t, kind, ids in topics_for(k, c["runs"][0]["cases"]):
            ids = [i + "@" + k for i in ids if i + "@" + k in relall]
            if ids: bubbles.append({"cell": k, "topic": t, "kind": kind, "n": len(ids), "x": round(float(np.mean([relall[i] for i in ids])), 4), "y": round(float(np.mean([spec[i] for i in ids])), 4)})
    topic_order = []
    for b in bubbles:
        if b["topic"] not in topic_order: topic_order.append(b["topic"])
    topic_order = [t for t in topic_order if not any(b["kind"] == "cmp" and b["topic"] == t for b in bubbles)] + \
                  [t for t in topic_order if any(b["kind"] == "cmp" and b["topic"] == t for b in bubbles)]
    for b in bubbles: b["num"] = topic_order.index(b["topic"]) + 1
    (HERE / "bubble_results.json").write_text(json.dumps(bubbles, indent=2))
    L, R, T, B = 150, 900, 70, 600
    xs = [b["x"] for b in bubbles]; XMIN, XMAX = max(0, min(xs) - 0.03), max(xs) + 0.03; YMIN, YMAX = -0.05, 1.05
    def px(x): return L + (R - L) * (x - XMIN) / (XMAX - XMIN)
    def py(v): return B - (B - T) * (v - YMIN) / (YMAX - YMIN)
    grid = "".join(f'<line x1="{L}" y1="{py(g):.1f}" x2="{R}" y2="{py(g):.1f}" stroke="#f4f5f6"/><text x="{L-14}" y="{py(g)+5:.1f}" text-anchor="end" font-size="22" fill="#6b7280">{g:.1f}</text>' for g in [0, .2, .4, .6, .8, 1])
    grid += "".join(f'<text x="{px(g):.1f}" y="{B+32}" text-anchor="middle" font-size="20" fill="#6b7280">{g:.2f}</text>' for g in np.linspace(XMIN, XMAX, 6))
    body = ""
    for b in sorted(bubbles, key=lambda d: -d["n"]):
        col = active[b["cell"]]["color"]; r = 12 + 6 * b["n"] ** 0.5; dash = ' stroke-dasharray="5 3"' if b["kind"] == "cmp" else ""
        body += f'<circle cx="{px(b["x"]):.1f}" cy="{py(b["y"]):.1f}" r="{r:.1f}" fill="{col}" fill-opacity="0.5" stroke="{col}" stroke-width="1.5"{dash}/><text x="{px(b["x"]):.1f}" y="{py(b["y"])+6:.1f}" text-anchor="middle" font-size="16" font-weight="700" fill="#fff">{b["num"]}</text>'
    KX = R + 40; ky = T + 4; key = f'<text x="{KX}" y="{ky}" font-size="19" font-weight="700" fill="#374151">Cell (color)</text>'; ky += 28
    for k, c in active.items():
        key += f'<rect x="{KX}" y="{ky-14}" width="18" height="18" rx="4" fill="{c["color"]}" fill-opacity="0.7"/><text x="{KX+28}" y="{ky}" font-size="17" fill="#374151">{c["label"]}</text>'; ky += 26
    ky += 12; key += f'<text x="{KX}" y="{ky}" font-size="19" font-weight="700" fill="#374151">Topic (number)</text>'; ky += 28
    for i, t in enumerate(topic_order, 1):
        cmp = any(b["kind"] == "cmp" and b["topic"] == t for b in bubbles)
        dash = ' stroke-dasharray="3 2"' if cmp else ""
        key += f'<circle cx="{KX+9}" cy="{ky-6}" r="10" fill="#6b7280" fill-opacity="0.5" stroke="#6b7280"{dash}/><text x="{KX+9}" y="{ky-2}" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">{i}</text><text x="{KX+28}" y="{ky}" font-size="16" fill="#374151">{t[:46]}{" · probes" if cmp else ""}</text>'; ky += 25
    H = max(700, ky + 20)
    svg = (f'<svg viewBox="0 0 1420 {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Segoe UI,Roboto,sans-serif"><rect width="1420" height="{H}" fill="#fff"/>{grid}'
           f'<line x1="{L}" y1="{T}" x2="{L}" y2="{B}" stroke="#d1d5db"/><line x1="{L}" y1="{B}" x2="{R}" y2="{B}" stroke="#d1d5db"/>'
           f'<text x="{(L+R)/2:.0f}" y="{B+66}" text-anchor="middle" font-size="24" font-weight="600" fill="#374151">Domain relatedness (closeness to a real filing &rarr;)</text>'
           f'<text x="40" y="{(T+B)/2:.0f}" transform="rotate(-90 40 {(T+B)/2:.0f})" text-anchor="middle" font-size="24" font-weight="600" fill="#374151">Domain specificity (markers pinned /5 &uarr;)</text>{body}{key}</svg>')
    foot = f"Each bubble is a question topic ({src}) from run 1 of each cell; x = mean domain relatedness, y = mean specificity (company, period, statement, line item, verifiable answer); size = questions. Dashed = compliance probes (only where the runbook was supplied). 2 × 2 factorial rerun 2026-08-27."
    (HERE / "bubble_chart.html").write_text(shell("Question topics in domain space &mdash; documents &times; runbook", "FinanceBench golden sets &middot; 2 &times; 2 factorial rerun 2026-08-27 &middot; bubbles = topics over the questions", svg, foot, 1300))

    # ---------------- flow diagram: four panels
    orig = (HERE.parent / "golden_set_question_types.html").read_text()
    js_fn = orig[orig.find("const barW"):orig.find("const WITH=")]; css = orig[orig.find("<style>"):orig.find("</style>") + 8]
    panels = ""; specs = ""; init = ""
    for k, c in active.items():
        r = c["runs"][0]; tl = topics_for(k, r["cases"]); ncap, ncmp = len(r["cap"]), len(r["cmp"])
        capcol = "#5B8FF9" if c["docs"] else "#94a3b8"
        caplab = ("Grounded questions" if c["docs"] else "Ungrounded questions (no evidence, no answers)")
        nodes = [dict(id="r", col=0, label=c["label"], value=50, color="#9aa0a6"), dict(id="cap", col=1, label=caplab, value=ncap, color=capcol),
                 dict(id="cmp", col=1, label="Agent-compliance / safety", value=ncmp, color="#E8684A", **({} if ncmp else dict(ghost=True, ghostGap=True)))]
        links = [{"from": "r", "to": "cap", "value": ncap, "color": capcol}] + ([{"from": "r", "to": "cmp", "value": ncmp, "color": "#E8684A"}] if ncmp else [])
        for i, (t, kd, ids) in enumerate(tl):
            nodes.append(dict(id=f"t{i}", col=2, label=t[:46], value=len(ids), color="#cdd0d4"))
            links.append({"from": "cap" if kd == "cap" else "cmp", "to": f"t{i}", "value": len(ids), "color": capcol if kd == "cap" else "#E8684A"})
        specs += f"const SPEC_{k}={json.dumps(dict(n=50, nodes=nodes, links=links))};\n"; init += f'document.getElementById("p{k}").innerHTML=buildSVG(SPEC_{k});'
        panels += f'<div class="panel"><div class="ptitle">{c["label"]} <span class="chip {"good" if ncmp else "warn"}">{ncap} capability &middot; {ncmp} compliance probes</span></div><div class="pnote">run 1 of {len(c["runs"])} &middot; {len(tl)} topics &middot; {sum(1 for _,kd,_ in tl if kd=="cmp")} compliance criteria probed</div><div id="p{k}"></div></div>'
    html = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/><title>Golden-set question topics — documents × runbook (rerun 2026-08-27)</title>{css}</head><body><div class="wrap">
<style>.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}} .grid .panel{{margin:0}}</style>
<h1>Golden-set question topics — documents × runbook</h1>
<p class="sub">Topics: {src}. One system prompt and a 50-question budget in every cell; only the data sections differ (filing evidence text without the benchmark's Q&amp;A; the Domain Compliance Runbook). Each diagram flows root → sub-category → topic.</p>
<div class="grid">{panels}</div><p class="sub">Sources: rerun_2026-08-27_2x2/cell_*/run1/golden_set_*.json. Self-contained — inline SVG, no network.</p></div>
<script>{js_fn}{specs}{init}</script></body></html>'''
    (HERE / "golden_set_question_types.html").write_text(html)

    # ---------------- coverage table: mean +- sd over runs, four columns
    def row(r):
        crit = {}
        for c in r["cmp"]:
            for p in c.get("probes_criteria") or []: crit[p] = crit.get(p, 0) + 1
        covered = {p for c in r["cases"] for p in (c.get("probes_criteria") or [])}
        return dict(cap=len(r["cap"]), named=sum(1 for c in r["cases"] if c.get("company")), answered=sum(1 for c in r["cap"] if (c.get("expected") or "").strip()),
                    verifiable=sum(1 for c in r["cap"] if figure_verifiable(c)), decline=sum(1 for c in r["cap"] if DECLINE.search((c["input"] or "") + " " + (c.get("expected") or ""))),
                    probes=len(r["cmp"]), covered=len(covered & set(CRITERIA)), crit=crit)
    agg = {}
    for k, c in active.items():
        rs = [row(r) for r in c["runs"]]
        agg[k] = {f: msd([x[f] for x in rs]) for f in ("cap", "named", "answered", "verifiable", "decline", "probes", "covered")}
        agg[k]["crit"] = {p: msd([x["crit"].get(p, 0) for x in rs])[0] for p in CRITERIA if any(x["crit"].get(p) for x in rs)}
        agg[k]["k"] = len(rs)
    def fmt(m, sd, k): return f"{m:.0f}" if k == 1 or sd == 0 else f"{m:.1f} ± {sd:.1f}"
    def cell(txt, ok): return f'<td class="{"ok" if ok else "no"}">{txt}</td>'
    trs = [("Golden-set questions (per run)", lambda a: ("50", True)),
           ("Capability / metric questions", lambda a: (fmt(*a["cap"], a["k"]), a["cap"][0] > 0)),
           ("&#8627; naming a specific issuer (of 50)", lambda a: (fmt(*a["named"], a["k"]), a["named"][0] > 0)),
           ("&#8627; with a grounded expected answer", lambda a: (fmt(*a["answered"], a["k"]), a["answered"][0] > 0)),
           ("&#8627; answer figure verifiable in raw filing data", lambda a: (fmt(*a["verifiable"], a["k"]), a["verifiable"][0] > 0)),
           ("&#8627; edge-case / decline (metric not meaningful, line item absent)", lambda a: (fmt(*a["decline"], a["k"]), a["decline"][0] > 0)),
           ("Compliance / safety probes", lambda a: (fmt(*a["probes"], a["k"]) + ("<br><span class='sub'>" + " · ".join(f"{p.split(' ')[0].split('&')[0]} {v:.0f}" for p, v in a["crit"].items()) + "</span>" if a["crit"] else "<br><span class='sub'>none generated</span>"), a["probes"][0] > 0)),
           ("Compliance criteria covered (of 5)", lambda a: (fmt(*a["covered"], a["k"]), a["covered"][0] >= 5))]
    tbody = "".join(f'<tr><td class="cap">{n}</td>' + "".join(cell(*fn(agg[k])) for k in active) + "</tr>" for n, fn in trs)
    th = "".join(f'<th style="color:{c["color"]}">{c["label"].split(" · ")[0]}<span class="sub">{c["label"].split(" · ")[1]} · k={agg[k]["k"]}</span></th>' for k, c in active.items())
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>What each golden set can cover — documents × runbook (rerun 2026-08-27)</title>
<style>body{{margin:0;background:#f4f6f8;color:#1f2d3d;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;padding:34px}}
.wrap{{max-width:1180px;margin:0 auto}} h1{{font-size:18px;letter-spacing:.04em;color:#586574;text-transform:uppercase;margin:0 0 10px}}
.lede{{color:#7b8794;font-size:15px;line-height:1.6;margin:0 0 22px}} .card{{background:#fff;border:1px solid #e6e9ec;border-radius:16px;padding:10px 18px 18px}}
table{{width:100%;border-collapse:collapse}} th,td{{text-align:center;padding:15px 12px;vertical-align:middle;border-bottom:1px solid #edf0f2;font-size:15px}}
th:first-child,td:first-child{{text-align:left;width:32%}} thead th{{color:#7b8794;font-weight:700}} thead th .sub,td .sub{{display:block;font-weight:500;font-size:12.5px;color:#7b8794;margin-top:3px}}
.cap{{font-weight:700;color:#23313f}} td.ok{{color:#2f7a44;font-weight:600}} td.no{{color:#9aa3ad}}</style></head><body><div class="wrap">
<h1>What each golden set can cover — 2 × 2 factorial, mean ± sd over runs</h1>
<p class="lede">All four columns are <b>measured</b> generated golden sets (same system prompt, 50-question budget; only the data sections differ). <b>Documents</b> = filing evidence text with the benchmark's questions and answers removed; <b>runbook</b> = the extracted Domain Compliance Runbook. Counts computed from the committed JSON by <code>make_2x2_plots.py</code>.</p>
<div class="card"><table><thead><tr><th>Capability</th>{th}</tr></thead><tbody>{tbody}</tbody></table></div>
<p class="lede" style="margin-top:18px">Documents make answers gradeable; the runbook is what adds compliance probes, criteria coverage, and decline / applicability cases — in both the with- and without-documents columns.</p></div></body></html>'''
    (HERE / "coverage_table.html").write_text(html)
    print("wrote figures into", HERE)

if __name__ == "__main__":
    main()
