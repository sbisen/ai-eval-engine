# Results

Committed evaluation artifacts backing the SciPy 2026 paper. These are produced by
`ai-eval-engine build ...` (see the top-level `README.md`) and are checked in here so the
paper's numbers are inspectable without rerunning the pipeline.

## ScienceAgentBench ablation (CC-BY-4.0 — committed in full)

ScienceAgentBench tasks are CC-BY-4.0 (see `data/scienceagentbench/NOTICE`), so the full
bundles are committed:

| Directory | Build |
|---|---|
| `sab/` | **with** extracted `DomainContext` (Step 1 on) |
| `sab_nocontext/` | **without** domain context (Step 1 off) |

Each bundle holds `golden_set.json`, the generated `eval_*.py`, `eval_report.json`,
`runbook.json`, `predictions.json`, and `index.html` (open it in a browser for the dashboard).
The with-context build adds execution-safety cases and a clustered runbook the generic build
lacks.

## FinanceBench ablation (CC-BY-NC-4.0 — aggregates only)

FinanceBench is **CC-BY-NC-4.0 (NonCommercial)** and is **not** redistributed in this
MIT-licensed repo. Only license-safe aggregate reports are committed — per-case answer text
(the `detail` field carrying gold and predicted answers) has been stripped:

| File | Build |
|---|---|
| `financebench_aggregate.json` | **with** domain context (n=66, includes safety cases) |
| `financebench_nocontext_aggregate.json` | **without** domain context (n=61) |

Retained: `pass_rate`, `domain_accuracy`, `grounding_rate`, `safety_score`, per-company
`by_category` metrics, and per-case scores (`passed`, `correctness`, `grounding`,
`failure_type`). Removed: all reproduced question / answer / evidence text.

### Reproducing the full FinanceBench bundle

1. Obtain FinanceBench per `data/README.md` → `data/financebench/financebench.csv`.
2. Rerun the build:
   ```bash
   ai-eval-engine build --config configs/financebench.yaml \
     --out out/financebench --context out/financebench/context.json \
     --predictions out/financebench/preds_real.json
   ```

> The headline ablation is the **delta between the with- and without-context builds** scored on
> the *same* predictions, not any single agent score.

## Figures

The previous figure suite (`make_ablation_figure.py` + `fb_ablation`, `grounding_scatter`,
`okr_radar`, `per_company`) was **removed** — it misrepresented the data and is not trusted:

- The radar and the ablation bar chart **hardcoded the baseline safety score to `0.0`**, but
  the no-context run actually reports `safety_score = 0.9836`. The baseline lacks dedicated
  `safety_boundary` *test cases* (0 vs 5); it does **not** score 0 on safety. The charts
  conflated "no safety test cases" with "scored 0," manufacturing a collapse that isn't real.
- `per_company` plotted 33 companies at **n=2 each**, so every bar is forced to 0.0/0.5/1.0 —
  a quantization artifact, not a per-company signal.
- `grounding_scatter` added jitter directly onto the correctness value, pushing a [0,1] match
  score above 1.0 and below 0.

The committed JSONs above are the trustworthy record (every headline number recomputes exactly
from the per-case rows). Any future figures must read straight from these values with no
hardcoded substitutions, and must not present `n=2` slices as if they were stable rates.
