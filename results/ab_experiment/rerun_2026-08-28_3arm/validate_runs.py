"""Step-4 checks for the three-arm rerun: schema, benchmark-question overlap (calibrated: the June set that\nparaphrased FinanceBench scores mean 0.64 with 19/36 > 0.6; a blind arm that saw nothing scores ~0.40, 0 > 0.6),
grounding numbers present in evidence, probe counts. Prints a table and writes validation.json."""
import json, re, glob
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent.parent.parent
FB = [json.loads(l) for l in open(ROOT / "data/financebench/financebench_open_source.jsonl")]
EV = json.loads((HERE / "evidence_rows_no_qa.json").read_text())
ARMS = {"A": ("armA_docs_runbook", "wdc", True, True), "B": ("armB_docs_only", "doc", True, False), "C": ("armC_blind", "ndc", False, False)}
def words(s): return set(re.findall(r"\w+", (s or "").lower()))
def overlap(a, b):
    A, B = words(a), words(b); return len(A & B) / max(1, len(A))
def norm(s): return re.sub(r"[^0-9]", "", s or "")
out = {}
for arm, (d, pre, has_docs, has_rb) in ARMS.items():
    for f in sorted(glob.glob(str(HERE / d / "run*" / "golden_set_*.json"))):
        run = Path(f).parent.name; cases = json.loads(Path(f).read_text())["cases"]
        cap = [c for c in cases if c.get("question_type") != "compliance-probe"]; cmp = [c for c in cases if c.get("question_type") == "compliance-probe"]
        keys = {tuple(sorted(c)) for c in cases}
        exp_keys = ("company", "expected", "grounding", "id", "input", "question_type") + (("probes_criteria",) if has_rb else ())
        schema_ok = len(cases) == 50 and [c["id"] for c in cases] == [f"{pre}-{i:03d}" for i in range(1, 51)] and keys == {tuple(sorted(exp_keys))}
        ov = [max(overlap(c["input"], r["question"]) for r in FB) for c in cap]
        para = sum(1 for v in ov if v > 0.6); ov_mean = round(sum(ov) / max(1, len(ov)), 3)
        gnum_ok = 0
        if has_docs:
            for c in cap:
                co = (c.get("company") or "").lower(); blob = norm(" ".join(r["evidence"] for r in EV if co and co.split()[0] in r["company"].lower()))
                nums = [norm(x) for x in re.findall(r"\d[\d,\.]{2,}", c.get("grounding") or "")]
                gnum_ok += int(all(n in blob for n in nums if len(n) >= 3))
        rec = dict(arm=arm, run=run, n=len(cases), schema_ok=schema_ok, probes=len(cmp), refuse_ok=all(c["expected"] == "[REFUSE]" and c["grounding"] is None for c in cmp),
                   benchmark_question_overlap_mean=ov_mean, benchmark_question_overlap_gt_0_6=para,
                   grounding_numbers_ok=(f"{gnum_ok}/{len(cap)}" if has_docs else "n/a"),
                   answered=sum(1 for c in cap if (c.get("expected") or "").strip()), named_company=sum(1 for c in cases if c.get("company")),
                   criteria=sorted({p for c in cases for p in (c.get("probes_criteria") or [])}))
        out[f"{arm}/{run}"] = rec
        print(f"{arm} {run}: schema={schema_ok} probes={len(cmp)} refuse_ok={rec['refuse_ok']} overlap_mean={ov_mean} (>0.6: {para}) grounding_ok={rec['grounding_numbers_ok']} answered={rec['answered']} named={rec['named_company']} criteria={len(rec['criteria'])}")
(HERE / "validation.json").write_text(json.dumps(out, indent=1)); print("wrote validation.json")
