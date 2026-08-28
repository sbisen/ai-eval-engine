"""Rebuild the five ab_experiment figures for the 2026-08-27 three-arm rerun.

Reads (relative to this folder):
  armA_with_context/golden_set_with_domain_context_run1.json
  armB_raw_data_only/golden_set_raw_data_only_run1.json
  armC_blind/golden_set_without_domain_context_run1.json
  topic_model_assignments.json   (optional; hand-verified topics. If absent, NMF auto-topics)
Writes (into this folder only — originals in ../ are never touched):
  domain_accuracy_results.json, domain_accuracy_chart.html
  relatedness_results.json,     relatedness_boxplot.html
  bubble_results.json,          bubble_chart.html
  golden_set_question_types.html
  coverage_table.html
  topic_model_assignments.auto.json (NMF output, for hand verification)

Scoring differs from ../make_domain_accuracy_chart.py in ONE deliberate way: the same
rule-based scorer is applied to every arm (the original hard-coded a different scorer per
arm). It is rule-based, not an LLM judge, and is labeled as such in the chart.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import NMF

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
RAW = [json.loads(l) for l in open(ROOT / "data/financebench/financebench_open_source.jsonl")]

ARMS = [  # key, label, color, file
    ("C", "Blind (no data, no runbook)",  "#9aa3ad", "armC_blind/golden_set_without_domain_context_run1.json"),
    ("B", "Raw data only (no runbook)",   "#5aa47a", "armB_raw_data_only/golden_set_raw_data_only_run1.json"),
    ("A", "With context (data + runbook)","#3f6fb0", "armA_with_context/golden_set_with_domain_context_run1.json"),
]
PROBE = "compliance-probe"

PERIOD = re.compile(r"\bFY ?20\d\d\b|\b20\d\d\b|Q[1-4] ?FY?20\d\d", re.I)
STATEMENT = re.compile(r"income statement|statement of operations|statement of income|balance sheet|"
                       r"statement of financial position|cash ?flow|statement of earnings|statement of cash flows", re.I)
LINEITEM = re.compile(r"revenue|net income|capital expenditure|property, plant|receivable|inventor|ebitda|cost of|"
                      r"gross (profit|margin)|dividend|cash and cash|EPS|earnings per|operating (income|margin|expense)|"
                      r"tax rate|R&?D|research and development|goodwill|debt|equity|segment|margin|ratio|turnover|"
                      r"assets|liabilities|shares|free cash flow|working capital|sales", re.I)
DERIVED = re.compile(r"ratio|turnover|margin|growth|average|change|percent|%|working capital|\bDPO\b|"
                     r"year-over-year|compute|calculate", re.I)
DECLINE = re.compile(r"meaningful|not (a )?(useful|relevant|applicable)|does not apply|not applicable|applicab|"
                     r"if .* not .*(disclosed|broken out|reported)|say 0|decline|cannot be (computed|calculated|determined)|"
                     r"not (be )?computable|state (that|so) and explain|explain why not|if (it|this|that) (is|does) not|"
                     r"no (inventory|cost of goods sold|COGS)|does not (report|present|hold|carry)|not (a )?(reported|defined|presented)", re.I)

def norm(s): return re.sub(r"[^0-9]", "", s or "")
def ev_text(r):
    e = r.get("evidence")
    if isinstance(e, list):
        return " ".join(str(x.get("evidence_text", "") if isinstance(x, dict) else x) for x in e)
    return str(e or "")
CORPUS = [(r.get("question") or "") + " " + (r.get("answer") or "") + " " + ev_text(r) for r in RAW]
VEC = TfidfVectorizer(stop_words="english", ngram_range=(1, 1), min_df=1, sublinear_tf=True)
X = VEC.fit_transform(CORPUS)

def load_arm(path):
    d = json.loads((HERE / path).read_text())
    return d["cases"] if isinstance(d, dict) else d

def figure_verifiable(c):
    co = (c.get("company") or "").lower()
    nums = {norm(x) for x in re.findall(r"[\d][\d,\.]{2,}", c.get("expected") or "") if len(norm(x)) >= 3}
    if not co or not nums: return False
    for r in RAW:
        if co.split()[0] in (r.get("company") or "").lower():
            blob = norm((r.get("answer") or "") + " " + ev_text(r))
            if any(n in blob for n in nums): return True
    return False

def score(c):
    """Same rule for every arm. relevance: 1.0 if the question names a statement or line item,
    0.9 if generic finance. groundedness: figure verifiable in raw data 1.0 (0.75 if derived);
    named issuer + non-empty answer 0.55; named issuer only 0.5; company-less 0.12."""
    q = c.get("input") or ""
    rel = 1.0 if (STATEMENT.search(q) or LINEITEM.search(q)) else 0.9
    if figure_verifiable(c):
        g, why = (0.75, "derived metric computed from real line items") if DERIVED.search(q) else (1.0, "figure traces to a raw filing record")
    elif c.get("company") and (c.get("expected") or "").strip():
        g, why = 0.55, f"named issuer ({c['company']}), answer not matched to a raw figure"
    elif c.get("company"):
        g, why = 0.5, f"named issuer ({c['company']}), no answer"
    else:
        g, why = 0.12, "company-less template — verifies against no filing"
    return round((rel + g) / 2, 3), why

def relatedness(cases):
    s = cosine_similarity(VEC.transform([c["input"] for c in cases]), X).max(axis=1)
    return [float(v) for v in s]

def specificity(c):
    q = c.get("input") or ""
    return sum((bool(c.get("company")), bool(PERIOD.search(q)), bool(STATEMENT.search(q)),
                bool(LINEITEM.search(q)), figure_verifiable(c))) / 5.0

def stats(vals):
    v = np.array(vals, float); q1, med, q3 = np.percentile(v, [25, 50, 75])
    return {"n": len(v), "min": round(float(v.min()), 4), "q1": round(float(q1), 4), "median": round(float(med), 4),
            "q3": round(float(q3), 4), "max": round(float(v.max()), 4), "mean": round(float(v.mean()), 4)}

# ------------------------------------------------------------------ topics
STOP = set("company fiscal year fy latest recent reported report 10 10k form filing filings statement "
           "statements does did total amount using use per based information provided million millions usd "
           "billions billion end ended ending answer question what how much many state note rounded decimal".split())
def auto_topics(cases, k):
    txt = [c["input"] for c in cases]
    v = TfidfVectorizer(stop_words=list(STOP | set(TfidfVectorizer(stop_words="english").get_stop_words())),
                        ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    M = v.fit_transform(txt)
    k = max(2, min(k, len(cases) - 1))
    W = NMF(n_components=k, init="nndsvda", random_state=0, max_iter=600).fit_transform(M)
    H = NMF(n_components=k, init="nndsvda", random_state=0, max_iter=600).fit(M).components_
    terms = v.get_feature_names_out()
    names = [", ".join(terms[i] for i in H[t].argsort()[::-1][:3]) for t in range(k)]
    out = {}
    for c, w in zip(cases, W):
        out.setdefault(names[int(w.argmax())], []).append(c["id"])
    return out

def topics_for(arm_key, cases):
    """Return list of (topic, kind, ids). kind: cap | cmp."""
    hand = HERE / "topic_model_assignments.json"
    if hand.exists():
        d = json.loads(hand.read_text()).get(arm_key)
        if d:
            out = [(t, "cap", d["assignments"][t]) for t in d["capability_subtree_topics"]]
            out += [(t, "cmp", d["assignments"][t]) for t in d.get("compliance_subtree_topics", [])]
            return out
    cap = [c for c in cases if c.get("question_type") != PROBE]
    cmp = [c for c in cases if c.get("question_type") == PROBE]
    out = [(t, "cap", ids) for t, ids in auto_topics(cap, 6).items()]
    bycrit = {}
    for c in cmp:
        bycrit.setdefault((c.get("probes_criteria") or ["(untagged)"])[0], []).append(c["id"])
    out += [(t, "cmp", ids) for t, ids in bycrit.items()]
    return out

# ------------------------------------------------------------------ shared html shell
def shell(title, sub, svg, foot, maxw=1180):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{title}</title>
<style>
 body{{margin:0;background:#f3f4f6;color:#111827;font-family:-apple-system,Segoe UI,Roboto,sans-serif;padding:32px}}
 .card{{max-width:{maxw}px;margin:0 auto;background:#fff;border:1px solid #e5e7eb;border-radius:14px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:24px 28px}}
 h1{{font-size:20px;margin:0 0 4px}} p.sub{{margin:0 0 16px;color:#6b7280;font-size:14px}}
 svg{{width:100%;height:auto;display:block}}
 .foot{{margin-top:18px;font-size:13px;line-height:1.55;color:#4b5563;border-top:1px solid #eee;padding-top:14px}}
</style></head><body><div class="card"><h1>{title}</h1><p class="sub">{sub}</p>{svg}<div class="foot">{foot}</div></div></body></html>'''

def main():
    arms = {}
    for key, label, color, path in ARMS:
        cases = load_arm(path)
        arms[key] = dict(label=label, color=color, cases=cases,
                         cap=[c for c in cases if c.get("question_type") != PROBE],
                         cmp=[c for c in cases if c.get("question_type") == PROBE])
        print(f"arm {key}: {len(cases)} cases, {len(arms[key]['cmp'])} probes")

    # ---------------- domain accuracy (rule-based, identical across arms)
    da = {}
    for key, a in arms.items():
        rows = []
        for c in a["cap"]:
            s, why = score(c)
            rows.append({"id": c["id"], "company": c.get("company") or "", "question": c["input"], "score": s, "reason": why})
        m = sum(r["score"] for r in rows) / len(rows)
        da[key] = {"n": len(rows), "domain_accuracy": round(m, 4), "rows": rows}
    summary = {"metric": "graded question domain accuracy = mean(relevance, groundedness vs raw FinanceBench JSON); questions, not answers; compliance probes excluded",
               "scorer": "rule-based (make_rerun_plots.py::score), identical for all arms — NOT an LLM judge",
               **{f"arm_{k}": {"label": arms[k]["label"], "n": da[k]["n"], "domain_accuracy": da[k]["domain_accuracy"]} for k in da}}
    (HERE / "domain_accuracy_results.json").write_text(json.dumps({"summary": summary, **{f"arm_{k}": da[k]["rows"] for k in da}}, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k.startswith("arm")}, indent=1))
    # chart: three bars
    L, R, T, B = 150, 1180, 120, 560; h = B - T
    def y(p): return B - h * p / 100
    cxs = [330, 665, 1000]; bw = 260
    grid = "".join(f'<line x1="{L}" y1="{y(p):.1f}" x2="{R}" y2="{y(p):.1f}" stroke="#e5e7eb"/><text x="{L-18}" y="{y(p)+6:.1f}" text-anchor="end" font-size="27" fill="#6b7280">{p}%</text>' for p in range(0, 101, 20))
    bars = ""
    for (key, a), cx in zip(arms.items(), cxs):
        pct = round(100 * da[key]["domain_accuracy"]); top = y(pct)
        bars += (f'<rect x="{cx-bw/2:.0f}" y="{top:.1f}" width="{bw}" height="{B-top:.1f}" rx="4" fill="{a["color"]}"/>'
                 f'<text x="{cx}" y="{top-16:.1f}" text-anchor="middle" font-size="38" font-weight="700" fill="#1f2937">{pct}%</text>'
                 f'<text x="{cx}" y="{B+40}" text-anchor="middle" font-size="24" fill="#374151">{a["label"].split(" (")[0]}</text>'
                 f'<text x="{cx}" y="{B+68}" text-anchor="middle" font-size="19" fill="#6b7280">({a["label"].split(" (")[1]}</text>')
    svg = f'<svg viewBox="0 0 1280 680" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Segoe UI,Roboto,sans-serif"><rect width="1280" height="680" fill="#fff"/>{grid}<line x1="{L}" y1="{T}" x2="{L}" y2="{B}" stroke="#d1d5db"/><line x1="{L}" y1="{B}" x2="{R}" y2="{B}" stroke="#d1d5db"/>{bars}</svg>'
    dA, dB, dC = (da[k]["domain_accuracy"] for k in "ABC")
    foot = (f"Rule-based scorer applied identically to all three arms (relevance: names a statement/line item; groundedness: figure verifiable "
            f"in the raw FinanceBench data, else named issuer, else company-less). Compliance probes excluded. "
            f"Blind {100*dC:.0f}% &rarr; raw data only {100*dB:.0f}% (+{100*(dB-dC):.0f} pts: what the data adds) &rarr; with context "
            f"{100*dA:.0f}% (+{100*(dA-dB):.0f} pts: what the extraction/runbook adds on top). Rerun 2026-08-27, k=1 per arm; "
            f"the June figure used a per-arm scorer and is not directly comparable.")
    (HERE / "domain_accuracy_chart.html").write_text(shell("Domain accuracy of generated questions &mdash; three arms", "FinanceBench golden sets &middot; rerun 2026-08-27 &middot; we test the questions, not the answers", svg, foot, 1040))

    # ---------------- relatedness boxplot (three boxes)
    rel = {k: [{"id": c["id"], "score": round(v, 4), "question": c["input"]} for c, v in zip(a["cap"], relatedness(a["cap"]))] for k, a in arms.items()}
    st = {k: stats([r["score"] for r in rel[k]]) for k in rel}
    ymax = round(max(s["max"] for s in st.values()) * 1.15 + 0.005, 2)
    L, R, T, B = 180, 1180, 90, 540; h = B - T
    def yy(v): return B - h * v / ymax
    grid = "".join(f'<line x1="{L}" y1="{yy(t):.1f}" x2="{R}" y2="{yy(t):.1f}" stroke="#e5e7eb"/><text x="{L-16}" y="{yy(t)+6:.1f}" text-anchor="end" font-size="27" fill="#6b7280">{t:.2f}</text>' for t in np.linspace(0, ymax, 6))
    body = ""; boxw = 200
    for (key, a), cx in zip(arms.items(), [350, 680, 1010]):
        s = st[key]; col = a["color"]; vals = sorted(r["score"] for r in rel[key])
        body += f'<line x1="{cx}" y1="{yy(s["max"]):.1f}" x2="{cx}" y2="{yy(s["min"]):.1f}" stroke="{col}" stroke-width="2"/>'
        for cap in (s["max"], s["min"]): body += f'<line x1="{cx-40}" y1="{yy(cap):.1f}" x2="{cx+40}" y2="{yy(cap):.1f}" stroke="{col}" stroke-width="2"/>'
        body += f'<rect x="{cx-boxw/2:.0f}" y="{yy(s["q3"]):.1f}" width="{boxw}" height="{abs(yy(s["q1"])-yy(s["q3"])):.1f}" rx="3" fill="{col}" fill-opacity="0.18" stroke="{col}" stroke-width="2.5"/>'
        body += f'<line x1="{cx-boxw/2:.0f}" y1="{yy(s["median"]):.1f}" x2="{cx+boxw/2:.0f}" y2="{yy(s["median"]):.1f}" stroke="{col}" stroke-width="3.5"/>'
        for i, v in enumerate(vals):
            body += f'<circle cx="{cx+((i*53)%100/100-0.5)*(boxw-40):.1f}" cy="{yy(v):.1f}" r="4.5" fill="{col}" fill-opacity="0.5"/>'
        body += f'<circle cx="{cx}" cy="{yy(s["mean"]):.1f}" r="7" fill="#fff" stroke="{col}" stroke-width="3"/>'
        body += f'<text x="{cx}" y="{B+38}" text-anchor="middle" font-size="27" font-weight="700" fill="#111827">{a["label"].split(" (")[0]}</text>'
        body += f'<text x="{cx}" y="{B+66}" text-anchor="middle" font-size="20" fill="#6b7280">median {s["median"]:.3f} &middot; mean {s["mean"]:.3f}</text>'
        body += f'<text x="{cx}" y="{B+90}" text-anchor="middle" font-size="19" fill="#9ca3af">n = {s["n"]}</text>'
    svg = f'<svg viewBox="0 0 1280 660" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Segoe UI,Roboto,sans-serif"><rect width="1280" height="660" fill="#fff"/><text x="44" y="{(T+B)/2:.0f}" transform="rotate(-90 44 {(T+B)/2:.0f})" text-anchor="middle" font-size="26" fill="#374151">Domain relatedness (max TF-IDF cosine)</text>{grid}<line x1="{L}" y1="{T}" x2="{L}" y2="{B}" stroke="#d1d5db"/><line x1="{L}" y1="{B}" x2="{R}" y2="{B}" stroke="#d1d5db"/>{body}</svg>'
    foot = ("Each generated question is scored by its max TF-IDF cosine similarity to the closest real FinanceBench record (question + answer + evidence). "
            "Offline and reproducible; compliance probes excluded. Box = IQR, line = median, hollow dot = mean, dots = questions. " +
            " &middot; ".join(f"<b>{arms[k]['label'].split(' (')[0]}</b> median {st[k]['median']:.3f}" for k in "CBA") + ". Rerun 2026-08-27, k=1.")
    (HERE / "relatedness_boxplot.html").write_text(shell("Per-question domain relatedness &mdash; three arms", "FinanceBench golden sets &middot; rerun 2026-08-27 &middot; distribution over the questions (not answers)", svg, foot, 1040))
    (HERE / "relatedness_results.json").write_text(json.dumps({**{f"arm_{k}_stats": st[k] for k in st}, **{f"arm_{k}": rel[k] for k in rel}}, indent=2))

    # ---------------- topics (auto NMF dump + bubble chart + flow diagram)
    auto = {}
    for key, a in arms.items():
        auto[key] = {"capability": auto_topics(a["cap"], 6),
                     "compliance": {t: ids for t, k2, ids in topics_for(key, a["cases"]) if k2 == "cmp"}}
    (HERE / "topic_model_assignments.auto.json").write_text(json.dumps(auto, indent=2))
    allcases = {c["id"]: c for a in arms.values() for c in a["cases"]}
    relall = {c["id"]: v for a in arms.values() for c, v in zip(a["cases"], relatedness(a["cases"]))}
    spec = {i: specificity(c) for i, c in allcases.items()}
    bubbles = []
    for key, a in arms.items():
        for t, kind, ids in topics_for(key, a["cases"]):
            ids = [i for i in ids if i in relall]
            if ids:
                bubbles.append({"arm": key, "topic": t, "kind": kind, "n": len(ids),
                                "x": round(float(np.mean([relall[i] for i in ids])), 4), "y": round(float(np.mean([spec[i] for i in ids])), 4)})
    for i, b in enumerate([b for k in "ABC" for b in bubbles if b["arm"] == k], 1): b["num"] = i
    (HERE / "bubble_results.json").write_text(json.dumps(bubbles, indent=2))
    L, R, T, B = 150, 900, 70, 600
    xs = [b["x"] for b in bubbles]; XMIN, XMAX = max(0, min(xs) - 0.03), max(xs) + 0.03; YMIN, YMAX = -0.05, 1.05
    def px(x): return L + (R - L) * (x - XMIN) / (XMAX - XMIN)
    def py(v): return B - (B - T) * (v - YMIN) / (YMAX - YMIN)
    grid = "".join(f'<line x1="{L}" y1="{py(g):.1f}" x2="{R}" y2="{py(g):.1f}" stroke="#f4f5f6"/><text x="{L-14}" y="{py(g)+5:.1f}" text-anchor="end" font-size="24" fill="#6b7280">{g:.1f}</text>' for g in [0, .2, .4, .6, .8, 1])
    grid += "".join(f'<text x="{px(g):.1f}" y="{B+32}" text-anchor="middle" font-size="22" fill="#6b7280">{g:.2f}</text>' for g in np.linspace(XMIN, XMAX, 6))
    body = ""
    for b in sorted(bubbles, key=lambda d: -d["n"]):
        col = arms[b["arm"]]["color"]; r = 12 + 6 * b["n"] ** 0.5
        dash = ' stroke-dasharray="5 3"' if b["kind"] == "cmp" else ""
        body += f'<circle cx="{px(b["x"]):.1f}" cy="{py(b["y"]):.1f}" r="{r:.1f}" fill="{col}" fill-opacity="0.5" stroke="{col}" stroke-width="1.5"{dash}/><text x="{px(b["x"]):.1f}" y="{py(b["y"])+6:.1f}" text-anchor="middle" font-size="17" font-weight="700" fill="#fff">{b["num"]}</text>'
    KX = R + 40; ky = T + 4; key = ""
    for k in "ABC":
        key += f'<text x="{KX}" y="{ky}" font-size="19" font-weight="700" fill="{arms[k]["color"]}">{arms[k]["label"]}</text>'; ky += 28
        for b in [b for b in bubbles if b["arm"] == k]:
            key += (f'<circle cx="{KX+10}" cy="{ky-6}" r="10" fill="{arms[k]["color"]}" fill-opacity="0.55" stroke="{arms[k]["color"]}"/><text x="{KX+10}" y="{ky-1}" text-anchor="middle" font-size="12" font-weight="700" fill="#fff">{b["num"]}</text>'
                    f'<text x="{KX+28}" y="{ky}" font-size="15" fill="#374151">{b["topic"][:44]} ({b["n"]}){" &middot; probes" if b["kind"]=="cmp" else ""}</text>'); ky += 24
        ky += 8
    H = max(700, ky + 20)
    svg = (f'<svg viewBox="0 0 1420 {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Segoe UI,Roboto,sans-serif"><rect width="1420" height="{H}" fill="#fff"/>{grid}'
           f'<line x1="{L}" y1="{T}" x2="{L}" y2="{B}" stroke="#d1d5db"/><line x1="{L}" y1="{B}" x2="{R}" y2="{B}" stroke="#d1d5db"/>'
           f'<text x="{(L+R)/2:.0f}" y="{B+66}" text-anchor="middle" font-size="26" font-weight="600" fill="#374151">Domain relatedness (closeness to a real filing &rarr;)</text>'
           f'<text x="40" y="{(T+B)/2:.0f}" transform="rotate(-90 40 {(T+B)/2:.0f})" text-anchor="middle" font-size="26" font-weight="600" fill="#374151">Domain specificity (markers pinned /5 &uarr;)</text>{body}{key}</svg>')
    src = "hand-verified topic_model_assignments.json" if (HERE / "topic_model_assignments.json").exists() else "automatic NMF topics (top-3 terms as labels; not yet hand-verified)"
    foot = (f"Each bubble is a question topic ({src}); x = mean domain relatedness, y = mean domain specificity (company, period, statement, line item, verifiable answer), size = questions. "
            "Dashed bubbles are compliance probes (present only where the runbook was supplied). Rerun 2026-08-27, k=1 per arm.")
    (HERE / "bubble_chart.html").write_text(shell("Question topics in domain space &mdash; three arms", "FinanceBench golden sets &middot; rerun 2026-08-27 &middot; bubbles = topics over the questions (not answers)", svg, foot, 1300))

    # ---------------- flow diagram (three panels, same JS renderer as the original)
    js_head = (HERE.parent / "golden_set_question_types.html").read_text()
    js_fn = js_head[js_head.find("const barW"):js_head.find("const WITH=")]
    panels = ""; specs = ""
    for k in "ABC":
        a = arms[k]; tl = topics_for(k, a["cases"]); ncap = len(a["cap"]); ncmp = len(a["cmp"])
        nodes = [dict(id="r", col=0, label=a["label"].split(" (")[0], value=50, color="#9aa0a6"),
                 dict(id="cap", col=1, label="Domain-grounded analysis" if k == "A" else ("Data-grounded questions" if k == "B" else "Ungrounded questions (no evidence, no answers)"), value=ncap, color="#5B8FF9" if k != "C" else "#94a3b8"),
                 dict(id="cmp", col=1, label="Agent-compliance / safety", value=ncmp, color="#E8684A", **({} if ncmp else dict(ghost=True, ghostGap=True)))]
        links = [dict(**{"from": "r", "to": "cap"}, value=ncap, color=nodes[1]["color"])]
        if ncmp: links.append(dict(**{"from": "r", "to": "cmp"}, value=ncmp, color="#E8684A"))
        for i, (t, kind, ids) in enumerate(tl):
            nodes.append(dict(id=f"t{i}", col=2, label=t[:46], value=len(ids), color="#cdd0d4"))
            links.append(dict(**{"from": "cap" if kind == "cap" else "cmp", "to": f"t{i}"}, value=len(ids), color=nodes[1]["color"] if kind == "cap" else "#E8684A"))
        specs += f"const SPEC_{k}={json.dumps(dict(n=50, nodes=nodes, links=links))};\n"
        panels += (f'<div class="panel"><div class="ptitle">{a["label"]} <span class="chip {"good" if ncmp else "warn"}">{ncap} capability &middot; {ncmp} compliance probes</span></div>'
                   f'<div class="pnote">{len(tl)} topics &middot; {sum(1 for t,kd,_ in tl if kd=="cmp")} compliance criteria probed</div><div id="p{k}"></div></div>')
    css = js_head[js_head.find("<style>"):js_head.find("</style>") + 8]
    html = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/><title>Golden-set question topics — three arms (rerun 2026-08-27)</title>{css}</head><body><div class="wrap">
<h1>Golden-set question topics — blind vs raw data vs data + runbook</h1>
<p class="sub">Topics: {src}. Same system prompt and 50-question budget in every arm; only the data sections differ. Each diagram flows root → sub-category → topic.</p>
{panels}
<p class="sub">Sources: rerun_2026-08-27/arm*/golden_set_*_run1.json. Self-contained — inline SVG, no network.</p></div>
<script>{js_fn}{specs}
document.getElementById("pA").innerHTML=buildSVG(SPEC_A);document.getElementById("pB").innerHTML=buildSVG(SPEC_B);document.getElementById("pC").innerHTML=buildSVG(SPEC_C);
</script></body></html>'''
    (HERE / "golden_set_question_types.html").write_text(html)

    # ---------------- coverage table (three measured arms)
    CRITERIA = ["Domain scope", "Citation & non-misleading disclosure", "MNPI & confidential-information safeguard", "No personal bias / no advice", "Escalate to Human"]
    def row(a):
        crit = {}
        for c in a["cmp"]:
            for p in c.get("probes_criteria") or []: crit[p] = crit.get(p, 0) + 1
        covered = {p for c in a["cases"] for p in (c.get("probes_criteria") or [])}
        return dict(total=len(a["cases"]), cap=len(a["cap"]), decline=sum(1 for c in a["cap"] if DECLINE.search((c["input"] or "") + " " + (c.get("expected") or ""))),
                    probes=len(a["cmp"]), crit=crit, covered=len(covered & set(CRITERIA)),
                    named=sum(1 for c in a["cases"] if c.get("company")), answered=sum(1 for c in a["cap"] if (c.get("expected") or "").strip()),
                    verifiable=sum(1 for c in a["cap"] if figure_verifiable(c)))
    R_ = {k: row(arms[k]) for k in "CBA"}
    def cell(k, txt, ok): return f'<td class="{"ok" if ok else "no"}">{txt}</td>'
    def probes_txt(r): return " &middot; ".join(f"{p.split(' ')[0].split('&')[0].strip()} {n}" for p, n in r["crit"].items()) if r["crit"] else "none generated"
    trs = [("A golden set exists to test against", lambda r: (f'✓ {r["total"]} questions', True)),
           ("Domain capability / metric questions", lambda r: (f'{r["cap"]} test{"s" if r["cap"]!=1 else ""}', r["cap"] > 0)),
           ("&#8627; naming a specific issuer", lambda r: (f'{r["named"]} of {r["total"]}', r["named"] > 0)),
           ("&#8627; with a grounded expected answer", lambda r: (f'{r["answered"]} of {r["cap"]}', r["answered"] > 0)),
           ("&#8627; answer figure verifiable in raw filing data", lambda r: (f'{r["verifiable"]} of {r["cap"]}', r["verifiable"] > 0)),
           ("&#8627; edge-case / decline (metric not meaningful, missing line item)", lambda r: (f'{r["decline"]} test{"s" if r["decline"]!=1 else ""}', r["decline"] > 0)),
           ("Compliance / safety probes", lambda r: (f'{r["probes"]} test{"s" if r["probes"]!=1 else ""}<br><span class="sub">{probes_txt(r)}</span>', r["probes"] > 0)),
           ("Compliance criteria covered (of 5)", lambda r: (f'{r["covered"]} of 5', r["covered"] == 5))]
    tbody = "".join(f'<tr><td class="cap">{name}</td>' + "".join(cell(k, *fn(R_[k])) for k in "CBA") + "</tr>" for name, fn in trs)
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>What each golden set can cover — three arms (rerun 2026-08-27)</title>
<style>body{{margin:0;background:#f4f6f8;color:#1f2d3d;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;padding:34px}}
.wrap{{max-width:1180px;margin:0 auto}} h1{{font-size:18px;letter-spacing:.04em;color:#586574;text-transform:uppercase;margin:0 0 10px}}
.lede{{color:#7b8794;font-size:15px;line-height:1.6;margin:0 0 22px}} .card{{background:#fff;border:1px solid #e6e9ec;border-radius:16px;padding:10px 18px 18px}}
table{{width:100%;border-collapse:collapse}} th,td{{text-align:center;padding:16px 14px;vertical-align:middle;border-bottom:1px solid #edf0f2;font-size:15px}}
th:first-child,td:first-child{{text-align:left;width:34%}} thead th{{color:#7b8794;font-weight:700}} thead th .sub,td .sub{{display:block;font-weight:500;font-size:13px;color:#7b8794;margin-top:3px}}
.cap{{font-weight:700;color:#23313f}} td.ok{{color:#2f7a44;font-weight:600}} td.no{{color:#9aa3ad}} th.a{{color:#3f6fb0}} th.b{{color:#5aa47a}} th.c{{color:#7b8794}}</style></head><body><div class="wrap">
<h1>What each golden set can cover — three measured arms</h1>
<p class="lede">All three columns are <b>measured</b> generated golden sets from the 2026-08-27 rerun (same system prompt, 50-question budget; only the data sections differ). Counts computed from the committed JSON by <code>make_rerun_plots.py</code>.</p>
<div class="card"><table><thead><tr><th>Capability</th><th class="c">Blind<span class="sub">no data, no runbook</span></th><th class="b">Raw data only<span class="sub">FinanceBench rows, no runbook</span></th><th class="a">With context<span class="sub">rows + compliance runbook</span></th></tr></thead><tbody>{tbody}</tbody></table></div>
<p class="lede" style="margin-top:18px">Compliance probes appear only where the runbook's criteria were supplied — the raw-data arm isolates what the extraction adds on top of the data.</p></div></body></html>'''
    (HERE / "coverage_table.html").write_text(html)
    print("wrote 5 html + results json into", HERE)

if __name__ == "__main__":
    main()
