# ai-eval-engine

**Domain-aware evaluation for production AI agents.**

> *AI agents are enabling powerful automation across industries — but shipping one surfaces a question most teams can't answer: is my agent actually correct, or just confident?*

ai-eval-engine is an open-source Python framework implementing the **Five-Step Framework** for domain-aware agent evaluation — so teams can finally measure what actually matters: correctness.

---

## The Problem

Generic eval tools measure hallucinations, latency, and token count. But none answer what matters: *did the agent do the right thing for this domain?* A SQL agent over a financial schema and a RAG agent over medical documents require fundamentally different correctness criteria — criteria that only exist with domain context.

Manually labeled golden sets are the most common approach, but they go stale the moment the data changes, the prompt updates, or a new use case emerges. Each team starts from scratch, builds in isolation, and ends up with non-reproducible eval pipelines that don't scale.

**ai-eval-engine closes this gap.**

---

## The Five-Step Framework

```
Step 1 — Pluggable Domain Context Ingestion
Step 2 — Automated Golden Set Generation  
Step 3 — Eval Script Generation + Scoring
Step 4 — Actionable Diagnosis
Step 5 — Post-Launch Monitoring Dashboard
```

### Step 1 — Pluggable Domain Context Ingestion
Provide a lightweight config — database secrets, agent system prompt, GitHub repo access, and user stories. The engine ingests this via a RAG pipeline, building the domain context that makes evaluation meaningful.

### Step 2 — Automated Golden Set Generation
An LLM generates a versioned, domain-grounded test set — representative queries, expected output format, and domain-specific edge cases. No manual labeling. Full user ownership. Human reviewable.

### Step 3 — Eval Script Generation + Scoring
An AI agent generates a Python eval script tailored to the agent type. Three scores per run:
- **Semantic correctness** — LLM-as-judge answer matching
- **Confidence score** — handles the probabilistic nature of LLM outputs
- **Format validation** — catches structural failures semantic scoring misses

### Step 4 — Actionable Diagnosis
Beyond scores — a diagnosis summary with:
- 🔴 High-risk flags for responses that should not ship
- 💡 Fix recommendations pointing to the exact source of failure: prompt, domain context, tool definition, or output schema

### Step 5 — Post-Launch Monitoring Dashboard
Accuracy over time against the golden set, latency flags, user metrics, and drift alerts.

---

## Why This Is Different

| Capability | RAGAS | DeepEval | Arize/Opik | **ai-eval-engine** |
|---|---|---|---|---|
| Domain context ingestion | ❌ | ❌ | ❌ | ✅ |
| Automated golden set generation | ❌ | Partial | ❌ | ✅ |
| Confidence scoring | ❌ | ❌ | ❌ | ✅ |
| Actionable fix recommendations | ❌ | ❌ | ❌ | ✅ |
| Drift-aware monitoring | ❌ | ❌ | ✅ | ✅ |

---

## Status

🚧 **Active development.** Framework architecture and Five-Step methodology defined. Implementation in progress.

---

## License

MIT

---

## Author

**Shivika Bisen**
- Speaker: Oracle Agentic AI Conference, AWS, Data Science Salon, Austin GenAI
- GitHub: [@sbisen](https://github.com/sbisen)
