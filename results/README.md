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

`make_ablation_figure.py` renders the paper's result figures from the JSONs above (PNG + PDF).
Every figure shows **only our own measured numbers**, always domain-aware (Step 1 on) versus
our no-context baseline (Step 1 off); published baselines stay in the paper prose, never in a
chart. Run from the repo root: `python3 results/make_ablation_figure.py`.

| File | Shows |
|---|---|
| `fb_ablation.{png,pdf}` | (a) FinanceBench scored metrics baseline vs domain-aware; (b) capability matrix of what domain context unlocks in the generated eval (both datasets) |
| `grounding_scatter.{png,pdf}` | per-case correctness vs grounding; the 18 well-grounded-but-incorrect definitional-mismatch cases |
| `okr_radar.{png,pdf}` | the 4 safety/quality OKRs; baseline collapses on the safety axis |
| `per_company.{png,pdf}` | FinanceBench pass rate by company — one flat number becomes a per-company map |
