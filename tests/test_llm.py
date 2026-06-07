"""The pluggable LLM backend seam — provider-agnostic, testable without an API key."""

from __future__ import annotations

import pytest

from ai_eval_engine import (
    AnthropicBackend,
    DomainContext,
    LLMBackend,
    extract_domain_context,
)
from ai_eval_engine.domain_context import SYSTEM_PROMPT, SYSTEM_PROMPT_TEXT


class FakeBackend(LLMBackend):
    """Records each call and returns a canned object — no network, no key."""

    def __init__(self, result):
        self.result = result
        self.calls: list[dict] = []

    def parse(self, *, system, user, schema):
        self.calls.append({"system": system, "user": user, "schema": schema})
        return self.result


def _ctx() -> DomainContext:
    return DomainContext(
        domain_name="x",
        summary="s",
        categories=[],
        safety_constraints=[],
        quality_signals=[],
    )


def test_llmbackend_is_abstract():
    with pytest.raises(TypeError):
        LLMBackend()


def test_anthropic_backend_is_an_llmbackend():
    # Constructing it must not require an API key (client is lazy).
    assert isinstance(AnthropicBackend(), LLMBackend)


def test_extract_uses_injected_backend_text_path(text_config_path):
    ctx = _ctx()
    fake = FakeBackend(ctx)
    out = extract_domain_context(text_config_path, backend=fake)

    assert out is ctx
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["schema"] is DomainContext
    assert call["system"] == SYSTEM_PROMPT_TEXT  # spec-oriented prompt for a text source
    assert "spec-test" in call["user"]


def test_extract_uses_injected_backend_csv_path(config_path):
    fake = FakeBackend(_ctx())
    extract_domain_context(config_path, backend=fake)

    call = fake.calls[0]
    assert call["system"] == SYSTEM_PROMPT  # data-oriented prompt for a csv source
    assert "Project: mini-test" in call["user"]
