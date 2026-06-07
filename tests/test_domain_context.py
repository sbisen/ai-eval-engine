"""DomainContext schema, prompt construction, and the public API surface."""

from __future__ import annotations


from ai_eval_engine import (
    DomainCategory,
    DomainContext,
    IntentCategory,
    build_user_message,
)
from ai_eval_engine.domain_context import SYSTEM_PROMPT


def test_intentcategory_is_alias_for_domaincategory():
    assert IntentCategory is DomainCategory


def test_domain_context_validates_and_serializes():
    ctx = DomainContext(
        domain_name="Banking support",
        summary="Customer-support intents for retail banking.",
        categories=[
            DomainCategory(
                name="card_arrival",
                description="Asking when a card will arrive",
                example_queries=["where is my card", "has my card shipped"],
            )
        ],
        safety_constraints=[
            {
                "name": "no_financial_advice",
                "description": "Route, do not advise on loans.",
                "severity": "critical",
                "rationale": "Regulated financial guidance must not be improvised.",
            }
        ],
        quality_signals=[{"name": "skew", "description": "Some intents are rare."}],
    )
    # Round-trips through JSON (this is the artifact downstream steps consume).
    restored = DomainContext.model_validate_json(ctx.model_dump_json())
    assert restored.categories[0].name == "card_arrival"
    assert restored.safety_constraints[0].severity == "critical"


def test_domain_context_json_schema_is_well_formed():
    schema = DomainContext.model_json_schema()
    assert schema["type"] == "object"
    for field in ("domain_name", "summary", "categories", "safety_constraints"):
        assert field in schema["properties"]


def test_build_user_message_embeds_project_and_rows():
    sample = [{"text": "hi", "category": "a"}]
    msg = build_user_message("acme", "support utterances", sample)
    assert "Project: acme" in msg
    assert "support utterances" in msg
    assert "category=" in msg


def test_system_prompt_is_non_empty():
    assert "Domain Context Extractor" in SYSTEM_PROMPT
    assert len(SYSTEM_PROMPT) > 200
