# Generation prompts behind the FinanceBench golden sets (supplementary)

This file answers the reviewer request to publish the exact prompts behind the two golden
sets in this directory and to say which reading of the "0 compliance probes" result applies.

## Provenance, stated plainly

1. **June 2026 run** (`golden_set_with_domain_context.json`, `golden_set_without_domain_context.json`).
   The exact prompt text was not archived at the time and is not recoverable. An earlier
   version of this file presented the code's `GENERATION_SYSTEM_PROMPT` as verbatim; that was
   wrong — the committed cases use a different schema (`question_type` / `probes_criteria`,
   no `kind` / `difficulty` / `rationale`) than that prompt requests. A best-effort
   reconstruction, derived from the artifacts themselves, is in `PROMPTS_RECONSTRUCTED.md`.
   The June run also handed the generator FinanceBench rows *including their question and
   answer fields*, so its with-context questions are largely paraphrases of the benchmark.

2. **2026-08-27 factorial rerun** (`rerun_2026-08-27_2x2/`) — the canonical, fully archived
   experiment. Every run's `prompt_system.txt` and `prompt_user.txt` are committed exactly as
   sent, with a `run_meta.json` (model, timestamps). The prompts are reproduced in
   [`rerun_2026-08-27_2x2/PROMPTS.md`](rerun_2026-08-27_2x2/PROMPTS.md). Design: one system
   prompt for all cells; factors **documents** (filing evidence text only — the benchmark's
   questions and answers removed) × **runbook** (the Domain Compliance Runbook); k = 3
   generation runs per cell. An intermediate three-arm rerun (`rerun_2026-08-27/`) is kept
   for the record; it still exposed the benchmark Q&A and is superseded.

## Which reading of "0 compliance probes" applies

The shared system prompt never asks for refusal, out-of-scope, or safety cases; it says
explicitly that if no runbook is provided the generator must not author them. Compliance
probes are requested only in the runbook-conditional section, synthesized from the runbook's
five criteria. Every cell without the runbook therefore produces 0/50 probes **by
construction**, and every cell with it produces ~14 — with or without documents. This is
the reading the paper states in §Results.

## Scoring note

The "domain accuracy" figures are produced by a **rule-based scorer applied identically to
every cell** (`rerun_2026-08-27/make_rerun_plots.py::score`), not by an LLM judge. The June
`make_domain_accuracy_chart.py` used a different scorer per arm; its numbers are not
comparable and are not used in the revised paper.
