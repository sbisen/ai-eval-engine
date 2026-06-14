"""AI Eval Engine — domain-aware evaluation for production AI agents."""

from dotenv import load_dotenv

load_dotenv(override=False)

__version__ = "0.1.0"

from ai_eval_engine.artifacts import format_artifacts, load_text_artifacts
from ai_eval_engine.config import (
    CsvSource,
    ProjectConfig,
    TaskSpec,
    TextSource,
    load_config,
)
from ai_eval_engine.dashboard import render_dashboard
from ai_eval_engine.domain_context import (
    DomainCategory,
    DomainContext,
    IntentCategory,
    QualitySignal,
    SafetyConstraint,
    build_artifacts_message,
    build_user_message,
    extract_domain_context,
)
from ai_eval_engine.evaluation import (
    CaseResult,
    EvalReport,
    generate_eval_script,
    make_baseline_predictions,
    run_eval,
)
from ai_eval_engine.golden_set import (
    GoldenCase,
    GoldenSet,
    build_golden_set,
    generate_golden_set,
)
from ai_eval_engine.llm import DEFAULT_MODEL, AnthropicBackend, LLMBackend
from ai_eval_engine.pipeline import build
from ai_eval_engine.eval_learnings import Runbook, RunbookItem, update_runbook
from ai_eval_engine.sampling import format_sample, load_csv_sample

__all__ = [
    "DEFAULT_MODEL",
    "AnthropicBackend",
    "CaseResult",
    "CsvSource",
    "DomainCategory",
    "DomainContext",
    "EvalReport",
    "GoldenCase",
    "GoldenSet",
    "IntentCategory",
    "LLMBackend",
    "ProjectConfig",
    "QualitySignal",
    "Runbook",
    "RunbookItem",
    "SafetyConstraint",
    "TaskSpec",
    "TextSource",
    "__version__",
    "build",
    "build_artifacts_message",
    "build_golden_set",
    "build_user_message",
    "extract_domain_context",
    "format_artifacts",
    "format_sample",
    "generate_eval_script",
    "generate_golden_set",
    "load_config",
    "load_csv_sample",
    "load_text_artifacts",
    "make_baseline_predictions",
    "render_dashboard",
    "run_eval",
    "update_runbook",
]
