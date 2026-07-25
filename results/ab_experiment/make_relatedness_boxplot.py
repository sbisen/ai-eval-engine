"""Box plot: how DOMAIN-RELATED each generated question is, with vs without domain context.

We test the questions, not answers. Each question's "domain relatedness" = the max TF-IDF
cosine similarity of the question text to the closest single real FinanceBench filing record
(over all FinanceBench question + answer + evidence text). This is an objective, offline,
reproducible stand-in for "how close is this question to a real thing in the domain" — no
soft LLM confidence.

Both golden sets are finance questions, so both score in the same range and the distributions
overlap; the with-context set sits modestly higher because its questions use the actual
filing vocabulary (company names, specific line items, periods). Compliance/refusal probes
are excluded.

Outputs relatedness_boxplot.html (self-contained) and relatedness_results.json.
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def ev_text(r):
    e = r.get("evidence")
    if isinstance(e, list):
        return " ".join(str(x.get("evidence_text", "") if isinstance(x, dict) else x) for x in e)
    return str(e or "")


def load(p):
    d = json.loads((HERE / p).read_text())
    return d["cases"] if isinstance(d, dict) and "cases" in d else d


def relatedness():
    raw = [json.loads(l) for l in open(ROOT / "data/financebench/financebench_open_source.jsonl")]
    corpus = [(r.get("question") or "") + " " + (r.get("answer") or "") + " " + ev_text(r) for r in raw]
    wc = [c for c in load("golden_set_with_domain_context.json")
          if c.get("question_type") != "compliance-probe"]
    nc = load("golden_set_without_domain_context.json")

    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 1), min_df=1, sublinear_tf=True)
    X = vec.fit_transform(corpus)

    def sims(cases):
        s = cosine_similarity(vec.transform([c["input"] for c in cases]), X).max(axis=1)
        return [{"id": c["id"], "score": round(float(v), 4), "question": c["input"]}
                for c, v in zip(cases, s)]

    return sims(wc), sims(nc)


def stats(vals):
    v = np.array(vals, float)
    q1, med, q3 = np.percentile(v, [25, 50, 75])
    return {"n": len(v), "min": round(float(v.min()), 4), "q1": round(float(q1), 4),
            "median": round(float(med), 4), "q3": round(float(q3), 4),
            "max": round(float(v.max()), 4), "mean": round(float(v.mean()), 4)}


def boxplot(groups, ymax):
    PLOT_L, PLOT_R, PLOT_T, PLOT_B = 180, 1180, 90, 540
    plot_h = PLOT_B - PLOT_T
    def y(v): return PLOT_B - plot_h * v / ymax

    ticks = np.linspace(0, ymax, 6)
    grid = "".join(
        f'<line x1="{PLOT_L}" y1="{y(t):.1f}" x2="{PLOT_R}" y2="{y(t):.1f}" stroke="#e5e7eb"/>'
        f'<text x="{PLOT_L-16}" y="{y(t)+6:.1f}" text-anchor="end" font-size="27" fill="#6b7280">{t:.2f}</text>'
        for t in ticks)

    xs = [470, 830]
    boxw = 230
    body = ""
    for (label, color, rows), cx in zip(groups, xs):
        vals = [r["score"] for r in rows]
        st = stats(vals)
        body += (f'<line x1="{cx}" y1="{y(st["max"]):.1f}" x2="{cx}" y2="{y(st["min"]):.1f}" '
                 f'stroke="{color}" stroke-width="2"/>')
        for cap in (st["max"], st["min"]):
            body += (f'<line x1="{cx-40}" y1="{y(cap):.1f}" x2="{cx+40}" y2="{y(cap):.1f}" '
                     f'stroke="{color}" stroke-width="2"/>')
        body += (f'<rect x="{cx-boxw/2:.0f}" y="{y(st["q3"]):.1f}" width="{boxw}" '
                 f'height="{abs(y(st["q1"])-y(st["q3"])):.1f}" rx="3" fill="{color}" '
                 f'fill-opacity="0.18" stroke="{color}" stroke-width="2.5"/>')
        body += (f'<line x1="{cx-boxw/2:.0f}" y1="{y(st["median"]):.1f}" x2="{cx+boxw/2:.0f}" '
                 f'y2="{y(st["median"]):.1f}" stroke="{color}" stroke-width="3.5"/>')
        for i, v in enumerate(sorted(vals)):
            jit = ((i * 53) % 100 / 100 - 0.5) * (boxw - 40)
            body += f'<circle cx="{cx+jit:.1f}" cy="{y(v):.1f}" r="4.5" fill="{color}" fill-opacity="0.5"/>'
        body += f'<circle cx="{cx}" cy="{y(st["mean"]):.1f}" r="7" fill="#fff" stroke="{color}" stroke-width="3"/>'
        body += (f'<text x="{cx}" y="{PLOT_B+38}" text-anchor="middle" font-size="30" '
                 f'font-weight="700" fill="#111827">{label}</text>')
        body += (f'<text x="{cx}" y="{PLOT_B+68}" text-anchor="middle" font-size="24" '
                 f'fill="#6b7280">median {st["median"]:.3f} &middot; mean {st["mean"]:.3f}</text>')

    return f'''<svg viewBox="0 0 1280 640" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Segoe UI,Roboto,sans-serif">
  <rect width="1280" height="640" fill="#ffffff"/>
  <text x="44" y="{(PLOT_T+PLOT_B)/2:.0f}" transform="rotate(-90 44 {(PLOT_T+PLOT_B)/2:.0f})" text-anchor="middle" font-size="26" fill="#374151">Domain relatedness (max TF-IDF cosine)</text>
  {grid}
  <line x1="{PLOT_L}" y1="{PLOT_T}" x2="{PLOT_L}" y2="{PLOT_B}" stroke="#d1d5db"/>
  <line x1="{PLOT_L}" y1="{PLOT_B}" x2="{PLOT_R}" y2="{PLOT_B}" stroke="#d1d5db"/>
  {body}
</svg>'''


def main():
    w, n = relatedness()
    sw, sn = stats([r["score"] for r in w]), stats([r["score"] for r in n])
    print("with :", json.dumps(sw))
    print("without:", json.dumps(sn))

    ymax = round(max(sw["max"], sn["max"]) * 1.15 + 0.005, 2)
    GREY, BLUE = "#9aa3ad", "#3f6fb0"
    svg = boxplot([("Without context", GREY, n), ("With context", BLUE, w)], ymax)

    foot = ("Each <i>generated question</i> is scored by its <b>domain relatedness</b> &mdash; the max "
            "TF-IDF cosine similarity of the question text to the closest single real FinanceBench filing "
            "record (over all question + answer + evidence text). Objective, offline, hand-reproducible "
            "&mdash; not a soft judge confidence. Box = IQR, line = median, hollow dot = mean, faint dots "
            f"= individual questions. <b>With context</b>: median {sw['median']:.3f}, mean {sw['mean']:.3f} "
            f"(n={sw['n']}). <b>Without context</b>: median {sn['median']:.3f}, mean {sn['mean']:.3f} "
            f"(n={sn['n']}) &mdash; roughly a {round(100*(sw['median']-sn['median'])/sn['median'])}% higher "
            "median. Both are genuinely finance questions, so the distributions still overlap; the "
            "with-context set lands closer to real filing records because its questions name specific "
            "companies, line items, and periods drawn from the domain.")

    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Per-question domain relatedness &mdash; with vs without context</title>
<style>
 body{{margin:0;background:#f3f4f6;color:#111827;font-family:-apple-system,Segoe UI,Roboto,sans-serif;padding:32px}}
 .card{{max-width:1040px;margin:0 auto;background:#fff;border:1px solid #e5e7eb;border-radius:14px;
   box-shadow:0 1px 3px rgba(0,0,0,.06);padding:24px 28px}}
 h1{{font-size:20px;margin:0 0 4px}} p.sub{{margin:0 0 16px;color:#6b7280;font-size:14px}}
 svg{{width:100%;height:auto;display:block}}
 .foot{{margin-top:18px;font-size:13px;line-height:1.55;color:#4b5563;border-top:1px solid #eee;padding-top:14px}}
</style></head><body>
 <div class="card">
  <h1>Per-question domain relatedness &mdash; with vs without domain context</h1>
  <p class="sub">FinanceBench golden sets &middot; distribution over the questions (not answers)</p>
  {svg}
  <div class="foot">{foot}</div>
 </div>
</body></html>'''
    (HERE / "relatedness_boxplot.html").write_text(html)
    (HERE / "relatedness_results.json").write_text(json.dumps(
        {"with_context_stats": sw, "without_context_stats": sn,
         "with_context": w, "without_context": n}, indent=2))
    print("wrote relatedness_boxplot.html")


if __name__ == "__main__":
    main()
