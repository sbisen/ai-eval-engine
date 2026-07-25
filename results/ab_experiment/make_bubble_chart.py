"""Bubble chart: question TOPICS in domain-relatedness x domain-specificity space.

We test the questions, not answers. Each NMF topic (from topic_model_assignments.json) is
one bubble:
  x    = mean domain relatedness  (max TF-IDF cosine of the question to the closest real
         FinanceBench filing record)
  y    = mean domain specificity  (# of 5 anchors pinned down / 5: company, period,
         statement, line item, verifiable answer)
  size = number of questions in the topic
  color= with-context capability (blue) | with-context compliance/safety (orange) |
         without-context generic (grey)

The frame shows three clusters a bar/box chart can't: with-context capability topics land
top-right (specific AND grounded), the with-context safety topics sit mid/low-left (name an
entity but use little filing vocabulary), and the without-context topics line the bottom
(on-topic finance, but generic). Outputs bubble_chart.html (self-contained).
"""
from __future__ import annotations
import json
import re
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

PERIOD = re.compile(r"\bFY ?20\d\d\b|\b20\d\d\b|Q[1-4] ?FY?20\d\d", re.I)
STATEMENT = re.compile(r"income statement|statement of operations|statement of income|balance sheet|"
                       r"statement of financial position|cash ?flow|statement of earnings|"
                       r"statement of cash flows", re.I)
LINEITEM = re.compile(r"revenue|net income|capital expenditure|property, plant|receivable|inventor|"
                      r"ebitda|cost of|gross (profit|margin)|dividend|cash and cash|EPS|earnings per|"
                      r"operating (income|margin|expense)|tax rate|R&?D|research and development|goodwill|"
                      r"debt|equity|segment|margin|ratio|turnover|assets|liabilities|shares|free cash flow|"
                      r"working capital|sales", re.I)


def norm(s): return re.sub(r"[^0-9]", "", s or "")
def ev_text(r):
    e = r.get("evidence")
    if isinstance(e, list):
        return " ".join(str(x.get("evidence_text", "") if isinstance(x, dict) else x) for x in e)
    return str(e or "")


def load(p):
    d = json.loads((HERE / p).read_text())
    return d["cases"] if isinstance(d, dict) and "cases" in d else d


def build_scores():
    raw = [json.loads(l) for l in open(ROOT / "data/financebench/financebench_open_source.jsonl")]
    corpus = [(r.get("question") or "") + " " + (r.get("answer") or "") + " " + ev_text(r) for r in raw]
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 1), min_df=1, sublinear_tf=True)
    X = vec.fit_transform(corpus)

    cases = {c["id"]: c for c in load("golden_set_with_domain_context.json")}
    cases.update({c["id"]: c for c in load("golden_set_without_domain_context.json")})

    ids = list(cases)
    rel = cosine_similarity(vec.transform([cases[i]["input"] for i in ids]), X).max(axis=1)
    relatedness = {i: float(v) for i, v in zip(ids, rel)}

    def figure_verifiable(c):
        co = (c.get("company") or "").lower()
        nums = {norm(x) for x in re.findall(r"[\d][\d,\.]{2,}", c.get("expected") or "") if len(norm(x)) >= 3}
        for r in [r for r in raw if co and co.split()[0] in (r.get("company") or "").lower()]:
            if any(n and n in norm((r.get("answer") or "") + " " + ev_text(r)) for n in nums):
                return True
        return False

    def specificity(c):
        q = c.get("input") or ""
        flags = (bool(c.get("company")), bool(PERIOD.search(q)), bool(STATEMENT.search(q)),
                 bool(LINEITEM.search(q)), figure_verifiable(c))
        return sum(flags) / 5.0

    spec = {i: specificity(cases[i]) for i in ids}
    return relatedness, spec


def topics():
    d = json.loads((HERE / "topic_model_assignments.json").read_text())
    w = d["with_domain_context"]
    out = []
    for t in w["capability_subtree_topics"]:
        out.append((t, "cap", w["assignments"][t]))
    for t in w["compliance_subtree_topics"]:
        out.append((t, "cmp", w["assignments"][t]))
    wo = d["without_domain_context"]
    for t in wo["assignments"]:
        out.append((t + " ", "gen", wo["assignments"][t]))   # trailing space avoids name clash
    return out


# Two categories only: with context vs without context. (cap + cmp are both with-context;
# cmp is kept as a flag just to annotate the safety probes the blind generator never made.)
COLORS = {"cap": "#3f6fb0", "cmp": "#3f6fb0", "gen": "#9aa3ad"}
LABELS = {"with": "With context", "gen": "Without context"}


def main():
    rel, spec = build_scores()
    bubbles = []
    for name, kind, ids in topics():
        ids = [i for i in ids if i in rel]
        if not ids:
            continue
        bubbles.append({
            "topic": name.strip(), "kind": kind, "n": len(ids),
            "x": round(float(np.mean([rel[i] for i in ids])), 4),
            "y": round(float(np.mean([spec[i] for i in ids])), 4),
        })
    # number bubbles: with-context first (1..), then without-context
    order = [b for b in bubbles if b["kind"] != "gen"] + [b for b in bubbles if b["kind"] == "gen"]
    for i, b in enumerate(order, 1):
        b["num"] = i

    # ---- geometry (plot on the left, numbered key on the right)
    PLOT_L, PLOT_R, PLOT_T, PLOT_B = 150, 900, 70, 600
    XMIN, XMAX = 0.10, 0.36
    YMIN, YMAX = -0.05, 1.05
    def px(x): return PLOT_L + (PLOT_R - PLOT_L) * (x - XMIN) / (XMAX - XMIN)
    def py(y): return PLOT_B - (PLOT_B - PLOT_T) * (y - YMIN) / (YMAX - YMIN)
    def rad(n): return 12 + 6 * (n ** 0.5)

    # quadrant guide split (median relatedness; specificity midpoint)
    xsplit = px(0.21); ysplit = py(0.5)
    grid = (f'<line x1="{xsplit:.0f}" y1="{PLOT_T}" x2="{xsplit:.0f}" y2="{PLOT_B}" stroke="#eceef0" stroke-dasharray="4 4"/>'
            f'<line x1="{PLOT_L}" y1="{ysplit:.0f}" x2="{PLOT_R}" y2="{ysplit:.0f}" stroke="#eceef0" stroke-dasharray="4 4"/>')
    for gy in [0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        grid += (f'<line x1="{PLOT_L}" y1="{py(gy):.1f}" x2="{PLOT_R}" y2="{py(gy):.1f}" stroke="#f4f5f6"/>'
                 f'<text x="{PLOT_L-14}" y="{py(gy)+5:.1f}" text-anchor="end" font-size="24" fill="#6b7280">{gy:.1f}</text>')
    for gx in [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]:
        grid += f'<text x="{px(gx):.1f}" y="{PLOT_B+32:.1f}" text-anchor="middle" font-size="24" fill="#6b7280">{gx:.2f}</text>'

    # bubbles (largest first), number centered inside
    body = ""
    for b in sorted(bubbles, key=lambda d: -d["n"]):
        c = COLORS[b["kind"]]
        r = rad(b["n"]); cx, cy = px(b["x"]), py(b["y"])
        body += (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{c}" fill-opacity="0.5" '
                 f'stroke="{c}" stroke-width="1.5"/>'
                 f'<text x="{cx:.1f}" y="{cy+6:.1f}" text-anchor="middle" font-size="17" '
                 f'font-weight="700" fill="#ffffff">{b["num"]}</text>')

    # quadrant captions (faint)
    qcap = (f'<text x="{px(0.30):.0f}" y="{py(0.95):.0f}" text-anchor="middle" font-size="18" fill="#9bb0cf">specific &amp; grounded</text>'
            f'<text x="{px(0.135):.0f}" y="{py(0.46):.0f}" font-size="18" fill="#c2a59a">safety probes</text>'
            f'<text x="{px(0.30):.0f}" y="{py(0.06):.0f}" text-anchor="middle" font-size="18" fill="#aab0b6">on-topic but generic</text>')

    # numbered key on the right
    KX = PLOT_R + 40
    key = ""
    ky = PLOT_T + 4
    def section(title, items, ky):
        nonlocal key
        key += f'<text x="{KX}" y="{ky}" font-size="20" font-weight="700" fill="#374151">{title}</text>'
        ky += 30
        for b in items:
            key += (f'<circle cx="{KX+10}" cy="{ky-6}" r="10" fill="{COLORS[b["kind"]]}" fill-opacity="0.55" stroke="{COLORS[b["kind"]]}"/>'
                    f'<text x="{KX+10}" y="{ky-1}" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">{b["num"]}</text>'
                    f'<text x="{KX+28}" y="{ky}" font-size="17" fill="#374151">{b["topic"]} ({b["n"]})</text>')
            ky += 29
        return ky + 8
    ky = section("With context", [b for b in order if b["kind"] != "gen"], ky)
    ky = section("Without context", [b for b in order if b["kind"] == "gen"], ky)
    # size legend
    key += f'<text x="{KX}" y="{ky+6}" font-size="17" fill="#6b7280" font-weight="600">Bubble size = # questions</text>'

    svg = f'''<svg viewBox="0 0 1420 700" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Segoe UI,Roboto,sans-serif">
  <rect width="1420" height="700" fill="#ffffff"/>
  {grid}
  <line x1="{PLOT_L}" y1="{PLOT_T}" x2="{PLOT_L}" y2="{PLOT_B}" stroke="#d1d5db"/>
  <line x1="{PLOT_L}" y1="{PLOT_B}" x2="{PLOT_R}" y2="{PLOT_B}" stroke="#d1d5db"/>
  <text x="{(PLOT_L+PLOT_R)/2:.0f}" y="{PLOT_B+66:.0f}" text-anchor="middle" font-size="26" font-weight="600" fill="#374151">Domain relatedness  (closeness to a real filing &rarr;)</text>
  <text x="40" y="{(PLOT_T+PLOT_B)/2:.0f}" transform="rotate(-90 40 {(PLOT_T+PLOT_B)/2:.0f})" text-anchor="middle" font-size="26" font-weight="600" fill="#374151">Domain specificity  (markers pinned /5 &uarr;)</text>
  {qcap}
  {body}
  {key}
</svg>'''

    foot = ("Two golden sets, two colors. Each bubble is a <b>question topic</b> (NMF over the raw "
            "question text). <b>x</b> = mean domain relatedness (max TF-IDF cosine to the closest real "
            "FinanceBench filing record); <b>y</b> = mean domain specificity (anchors pinned /5: company, "
            "period, statement, line item, verifiable answer); <b>size</b> = number of questions. We test "
            "the questions, not answers. <span style='color:#3f6fb0'><b>With context</b></span> topics sit "
            "up and to the right — specific and close to real filings — and the set also spans a lower-left "
            "band of <i>safety / refusal</i> topics the <span style='color:#9aa3ad'><b>without-context</b></span> "
            "generator never produced. Without-context topics line the bottom: valid finance topics, but "
            "generic, so low specificity. Same axes, same metric — domain context moves whole topics up and "
            "to the right, and adds a safety dimension that otherwise does not exist.")

    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Question topics &mdash; relatedness vs specificity</title>
<style>
 body{{margin:0;background:#f3f4f6;color:#111827;font-family:-apple-system,Segoe UI,Roboto,sans-serif;padding:32px}}
 .card{{max-width:1180px;margin:0 auto;background:#fff;border:1px solid #e5e7eb;border-radius:14px;
   box-shadow:0 1px 3px rgba(0,0,0,.06);padding:24px 28px}}
 h1{{font-size:20px;margin:0 0 4px}} p.sub{{margin:0 0 12px;color:#6b7280;font-size:14px}}
 svg{{width:100%;height:auto;display:block}}
 .foot{{margin-top:14px;font-size:13px;line-height:1.55;color:#4b5563;border-top:1px solid #eee;padding-top:14px}}
</style></head><body>
 <div class="card">
  <h1>Question topics in domain space &mdash; with vs without domain context</h1>
  <p class="sub">FinanceBench golden sets &middot; bubbles = NMF topics over the questions (not answers)</p>
  {svg}
  <div class="foot">{foot}</div>
 </div>
</body></html>'''
    (HERE / "bubble_chart.html").write_text(html)
    (HERE / "bubble_results.json").write_text(json.dumps(bubbles, indent=2))
    for b in sorted(bubbles, key=lambda d: (d["kind"], -d["n"])):
        print(f'{b["kind"]:3} n={b["n"]:2} x={b["x"]:.3f} y={b["y"]:.3f}  {b["topic"]}')
    print("wrote bubble_chart.html")


if __name__ == "__main__":
    main()
