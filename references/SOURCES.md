# Reference papers — citation spine

PDFs in `pdfs/`; BibTeX in `references.bib`. Downloaded 2026-05-31 from arXiv.
**Verify author lists / venues / citation counts before final submission.**

## Core eval canon (lineage to build on)
| Key | Paper | Venue | arXiv |
|---|---|---|---|
| zheng2023llmjudge | Judging LLM-as-a-Judge (MT-Bench, Chatbot Arena) | NeurIPS 2023 D&B | https://arxiv.org/abs/2306.05685 |
| liang2023helm | HELM: Holistic Evaluation of Language Models | TMLR 2023 | https://arxiv.org/abs/2211.09110 |
| es2024ragas | RAGAS | EACL 2024 (demo) | https://arxiv.org/abs/2309.15217 |
| liu2023geval | G-Eval | EMNLP 2023 | https://arxiv.org/abs/2303.16634 |
| saadfalcon2024ares | ARES | NAACL 2024 | https://arxiv.org/abs/2311.09476 |

## Primary framework baselines (the frameworks reviewers will compare you to)
| Key | Framework | What it is | Source |
|---|---|---|---|
| aisi2024inspect | **Inspect AI** (UK AI Security Institute) | Leading *agentic* AI-safety eval framework. `Dataset/Solver/Scorer/Task`; agent scaffolds, tool use, sandboxing, dangerous-capability evals (GAIA, GDM, SWE-Bench). `pip install inspect-ai` | https://inspect.aisi.org.uk |
| confident2024deepeval | **DeepEval** (Confident AI) | pytest-style LLM/agent eval framework; component, trajectory, end-to-end metrics | https://github.com/confident-ai/deepeval |

**Differentiation (two axes — NOT "agentic vs. old"):**
1. *Domain* — Inspect targets frontier dangerous-capability/model-level safety; `ai-eval-engine` targets domain-specific compliance for production enterprise agents.
2. *Generation* — Inspect/DeepEval **run and score** evals a human authors; `ai-eval-engine` **generates** the golden set + safety runbook from ingested domain context. This is the non-commodity contribution.

Adapter seam: a `GoldenCase` can emit an Inspect `Task` (Dataset+Scorer) via a thin shim — interoperate, don't compete.

## Closest method neighbors (corpus→test set / criteria synthesis)
| Key | Paper | Venue | arXiv |
|---|---|---|---|
| guinet2024examgen | RAG eval via task-specific exam generation | ICML 2024 (Oral) | https://arxiv.org/abs/2405.13622 |
| shankar2024evalgen | Who Validates the Validators? (EvalGen) | UIST 2024 | https://arxiv.org/abs/2404.12272 |
| shankar2024spade | SPADE: data-quality assertions | VLDB 2024 | https://arxiv.org/abs/2401.03038 |

## Latest closest competitors (cite + differentiate)
| Key | Paper | Year | arXiv |
|---|---|---|---|
| ata2025 | Agent-Testing Agent (ATA) | 2025 | https://arxiv.org/abs/2508.17393 |
| testagent2024 | TestAgent (vertical-domain auto-benchmarking) | 2024 | https://arxiv.org/abs/2410.11507 |
| yao2024taubench | τ-bench (domain + policy compliance) | 2024 | https://arxiv.org/abs/2406.12045 |

## Surveys + domain-specific safety
| Key | Paper | Venue | arXiv |
|---|---|---|---|
| yehudai2025survey | A Survey on Evaluation of LLM-based Agents | 2025 | https://arxiv.org/abs/2503.16416 |
| mohammadi2025survey | Evaluation and Benchmarking of LLM Agents: A Survey | KDD 2025 | https://arxiv.org/abs/2507.21504 |
| hui2025trident | TRIDENT (finance/medicine/law safety) | 2025 | https://arxiv.org/abs/2507.21134 |
| wang2023decodingtrust | DecodingTrust | NeurIPS 2023 | https://arxiv.org/abs/2306.11698 |

## Context engineering (light related-work)
| Key | Paper | Venue | Source |
|---|---|---|---|
| zhang2026ace | Agentic Context Engineering (ACE) — the *paper* | ICLR 2026 | https://ace-agent.github.io (PDF also in repo root) |
| kayba2024aceframework | Agentic Context Engine (ACE) — the *PyPI package* (Kayba.ai); Agent/Reflector/SkillManager, in-context skillbook | v0.7.0 | https://pypi.org/project/ace-framework/ |

## How they map to the paper
- **Primary baseline (cite + differentiate first):** aisi2024inspect, confident2024deepeval
- **Build lineage on:** zheng2023llmjudge, liang2023helm, es2024ragas, liu2023geval, saadfalcon2024ares
- **Differentiate against (closest):** guinet2024examgen, shankar2024evalgen, shankar2024spade, ata2025, testagent2024, yao2024taubench
- **Safety lineage (cite, don't adopt their finance/med/legal data):** hui2025trident, wang2023decodingtrust
