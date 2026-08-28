# Three-arm rerun — 2026-08-28

Arms (one identical system prompt; only the data sections of the user message differ; k = 3 generations per arm; every run's `prompt_system.txt` / `prompt_user.txt` / `run_meta.json` archived):

| Arm | Folder | Input | Prefix |
|---|---|---|---|
| C — blind | `armC_blind/` | nothing | `ndc` |
| B — documents only | `armB_docs_only/` | 61 filing-evidence rows (`evidence_rows_no_qa.json`: company, doc_name, doc_type, evidence — FinanceBench `question`/`answer` withheld) | `doc` |
| A — documents + runbook | `armA_docs_runbook/` | the same 61 rows + `../domain_compliance_runbook.json` | `wdc` |

Why the Q&A fields are withheld: the discarded 2026-08-27 three-arm run handed arms A and B the benchmark's own questions and answers, so the "generated" sets reproduced the benchmark's targets. Withholding them is the structural safeguard; `validate_runs.py` also reports a calibrated benchmark-question overlap (the June set that demonstrably paraphrased FinanceBench scores mean 0.64 with 19/36 questions > 0.6; a blind arm that saw nothing scores ≈ 0.40 with 0 > 0.6; all nine runs here sit at 0.36–0.41 with ≤ 3 > 0.6).

Scripts: `validate_runs.py` (schema, overlap, grounding numbers, probes → `validation.json`), `make_3arm_plots.py` (all five figures; scorer in `../plot_common.py`, rule-based and identical for every arm — not an LLM judge), `export_figures.py` (paper PNGs into `figures/`). Hand-verified topics: `topic_model_assignments.json`. Scorer validation against blind hand labels: `scorer_validation/`.
