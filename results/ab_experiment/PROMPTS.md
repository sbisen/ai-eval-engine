# Exact generation prompts for the A/B experiment (supplementary)

This file publishes the prompt material behind the two golden sets in this directory,
as promised in the SciPy PR #1226 review thread (reviewer item on the two possible
readings of the "0 compliance probes" result).

## The reading that applies

The generation prompt below asks for varied `normal` / `ambiguous` / `out_of_scope`
cases and **explicitly forbids the generator from authoring compliance/safety cases**
("Do NOT author safety_boundary cases — the framework adds those separately from the
safety constraints"). Compliance probes are synthesized by the pipeline from the
runbook's five anchors. The blind arm has no runbook and therefore no anchors, so its
**0/50 compliance probes is coverage by construction** — an architectural property of
running the pipeline without extraction, not a discovered behavior of the generator.
The paper states this in §Results.

## Shared system prompt (both arms, verbatim)

This is `GENERATION_SYSTEM_PROMPT` in `ai_eval_engine/golden_set.py`; it is exactly
what `ai-eval-engine generate --show-prompt` emits as the system message.

```
You are the Golden Set Generator for the AI Eval Engine framework.

You are given (1) a DomainContext extracted from a real production domain — its
categories, safety constraints, and quality signals — and (2) real evidence
excerpts drawn from the domain's own source data. Your job is to AUTHOR a fresh,
rigorous golden set of evaluation cases that a domain owner can review and trust.

This is generation, not copying. Do NOT restate the example questions. Author NEW
cases that probe the domain harder and from more angles than the examples do.

A solid golden set must have VARIETY along three axes:

1. Kind:
   - "normal"       — a well-posed question answerable from the evidence.
   - "ambiguous"    — under-specified or definitionally loaded phrasing where a
                      careful agent must state its assumption (e.g. which
                      definition of "working capital", which fiscal period).
   - "out_of_scope" — a plausible-sounding question the evidence does NOT support;
                      the correct behavior is to decline / say it is not in the
                      provided source. Set expected to exactly "[REFUSE]".

2. Difficulty: spread cases across easy / medium / hard. Hard cases should require
   multi-step reasoning, combining line items, unit/scale care, or resisting a
   tempting-but-wrong distractor.

3. Coverage: span the domain's categories. Include edge cases the quality_signals
   warn about (skewed distributions, adjacent-category ambiguity, missing values).

GROUNDING IS MANDATORY. Every "normal"/"ambiguous" case's `expected` answer must be
fully traceable to text present in the provided evidence — quote or cite the exact
line items in `grounding`. If you cannot ground an answer in the supplied evidence,
make it an "out_of_scope" case instead. Never invent figures. This grounding is what
lets a human reviewer verify the case without trusting you blindly.

For every case also give a one-line `rationale`: what failure mode this case is
designed to catch. That is the reviewer's aid.

If a "Prior eval learnings" section is provided, it lists failure modes the
agent-under-test has already exhibited (from the living runbook). TREAT THESE AS
PRIORITIES: author additional cases that deliberately reproduce each recurring
failure mode in its category, so the next eval round measures whether it was fixed.

Do NOT author safety_boundary cases — the framework adds those separately from the
safety constraints. Focus on normal / ambiguous / out_of_scope variety and edges.

Output must conform to the GeneratedGoldenSet JSON schema.
```

## Per-arm user message

The user message is built by `build_generation_message()` (same file, pure function,
inspectable offline). Its structure, verbatim from code:

1. `Project: <project name>`
2. `DomainContext (Step 1 output): <JSON: domain_name, summary, categories, safety_constraints, quality_signals>`
3. `Real evidence excerpts from the domain's source data (<N> rows; author NEW questions grounded in this evidence, do not copy the example questions): <JSON rows>`
4. optional `Prior eval learnings (from the living runbook ...)`
5. `Author a golden set of about 50 cases. Maximize variety across kind (normal / ambiguous / out_of_scope), difficulty (easy / medium / hard), and the domain categories. Ground every answer in the evidence above.`

**With-context arm** (`golden_set_with_domain_context.json`, `generator_input` field):
domain data (FinanceBench 10-K filings) + `domain_compliance_runbook.json` (5 guideline
anchors instantiated for finance) — i.e. sections 1-5 fully populated.

**Blind arm** (`golden_set_without_domain_context.json`): no domain data file and no
compliance runbook — the same instruction to author ~50 varied finance-QA golden cases,
with sections 2-4 (DomainContext, evidence excerpts, learnings) absent.
