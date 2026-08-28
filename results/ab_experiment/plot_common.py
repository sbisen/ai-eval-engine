"""Shared scoring / relatedness / topic / html helpers for the ab_experiment rerun figures.

Extracted from the removed rerun_2026-08-27/make_rerun_plots.py; imported by
rerun_2026-08-27_2x2/make_2x2_plots.py and rerun_2026-08-28_3arm/make_3arm_plots.py.
The scorer (score) is rule-based and identical for every arm/cell; it is NOT an LLM judge.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import NMF

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RAW = [json.loads(l) for l in open(ROOT / "data/financebench/financebench_open_source.jsonl")]

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

