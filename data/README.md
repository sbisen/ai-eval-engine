# Datasets

The configs in `configs/` expect a single CSV per dataset with the columns noted
below. Sampling is deterministic, so once a CSV is in place
`ai-eval-engine sample --config ...` reproduces the exact Step-1 sample with no API key.

## What's committed vs. downloaded

| Dataset | License | In this repo? |
|---|---|---|
| **ScienceAgentBench** (`tasks.csv`) | CC-BY-4.0 | ✅ Committed, with attribution in [`scienceagentbench/NOTICE`](scienceagentbench/NOTICE) |
| **FinanceBench** | CC-BY-NC-4.0 (NonCommercial) | ⬇️ Download-only — see below |

FinanceBench is **NonCommercial**, which is incompatible with this repository's
permissive (MIT) license, so it is intentionally not committed: download it yourself
with the instructions below. ScienceAgentBench's task table is CC-BY-4.0 (permissive,
attribution only) and is shipped here so the anchor demo reproduces out of the box.

## ScienceAgentBench (anchor — structured, execution-scored)

Data-driven scientific coding tasks from real peer-reviewed papers; solutions are
Python programs scored by execution.

- Paper: <https://arxiv.org/abs/2410.05080>
- Site: <https://osu-nlp-group.github.io/ScienceAgentBench/>
- Code/data: <https://github.com/OSU-NLP-Group/ScienceAgentBench>
- Hugging Face: `osunlp/ScienceAgentBench`
- License: **CC-BY-4.0** (dataset). Already committed here as `tasks.csv` — see
  [`scienceagentbench/NOTICE`](scienceagentbench/NOTICE). You only need to re-download
  it if you want the per-task input datasets the generated programs run against (not
  committed; fetch from the upstream repo above).

`tasks.csv` is the task table with at least:

| column                | meaning                                        |
|-----------------------|------------------------------------------------|
| `instance_id`         | unique task id                                 |
| `domain`              | discipline / sub-area (used for stratification)|
| `task_inst`           | the natural-language task instruction          |
| `dataset_folder_tree` | the dataset the program must operate on        |
| `gold_program_name`   | reference solution file name                   |

## FinanceBench (contrast — open-ended, grounding-scored)

Open-book QA over real corporate 10-K filings, with evidence strings.

- Paper: <https://arxiv.org/abs/2311.11944>
- Code/data: <https://github.com/patronus-ai/financebench>
- Hugging Face: `PatronusAI/financebench`
- License: **CC-BY-NC-4.0** (NonCommercial) — not committed here; download it yourself.

Only the **150-question open-source subset** (`financebench_open_source.jsonl`) is
publicly available; the full 10,231-question benchmark is held back by Patronus AI.
That subset is what the demo uses. Convert it to `data/financebench/financebench.csv`
with at least:

| column          | meaning                                       |
|-----------------|-----------------------------------------------|
| `company`       | filing company (used for stratification)      |
| `doc_name`      | source filing                                 |
| `doc_type`      | filing type (e.g. 10-K)                       |
| `question`      | the question                                  |
| `answer`        | the reference answer                          |
| `evidence`      | supporting passage(s) from the filing         |
| `question_type` | question category                             |

### Download & convert (reproducible)

```sh
mkdir -p data/financebench
curl -sL https://raw.githubusercontent.com/patronus-ai/financebench/main/data/financebench_open_source.jsonl \
  -o data/financebench/financebench_open_source.jsonl
```

```python
# jsonl -> financebench.csv: flatten the evidence list and derive doc_type from doc_name
import pandas as pd, json, re

with open("data/financebench/financebench_open_source.jsonl") as f:
    recs = [json.loads(l) for l in f if l.strip()]

def doc_type(name):
    n = str(name).upper()
    if "10K" in n: return "10-K"
    if "10Q" in n: return "10-Q"
    if "8K" in n:  return "8-K"
    if "EARNINGS" in n: return "earnings"
    return "other"

def evidence_text(ev):
    return "\n\n---\n\n".join(
        e["evidence_text"].strip() for e in (ev or [])
        if isinstance(e, dict) and e.get("evidence_text"))

pd.DataFrame([{
    "financebench_id": r.get("financebench_id"), "company": r.get("company"),
    "doc_name": r.get("doc_name"), "doc_type": doc_type(r.get("doc_name")),
    "question": r.get("question"), "answer": r.get("answer"),
    "evidence": evidence_text(r.get("evidence")), "question_type": r.get("question_type"),
} for r in recs]).to_csv("data/financebench/financebench.csv", index=False)
```

## Optional — InfiAgent-DABench (reproducible tabular baseline)

Objective closed-form data-analysis QA in Python (603 questions / 124 CSVs); can run
as a larger sanity baseline. <https://arxiv.org/abs/2401.05507>
