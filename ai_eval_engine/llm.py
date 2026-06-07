"""Pluggable LLM backend seam.

A thin interface around the framework's model calls so the engine is not hardwired
to one provider. Every call the pipeline makes is a *structured* one — given a
system prompt, a user message, and a Pydantic schema, return a validated instance
of that schema. :class:`LLMBackend` is that one method.

The default :class:`AnthropicBackend` preserves today's exact behavior (Claude
Opus 4.8, typed structured output via ``messages.parse``, adaptive thinking). A
different provider — including a local/open model behind an OpenAI-compatible
server such as Ollama — only has to implement :meth:`LLMBackend.parse`, without
touching the pipeline. See the paper's Future Work for that extension.
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    import anthropic

#: Default model for the bundled Anthropic backend.
DEFAULT_MODEL = "claude-opus-4-8"

T = TypeVar("T", bound=BaseModel)


class LLMBackend(abc.ABC):
    """One structured call: ``(system, user, schema) -> validated schema instance``.

    Implement this to plug in a provider. The framework never assumes anything
    beyond this method, so a backend is free to use native structured output
    (Anthropic) or a JSON-schema-prompt-and-validate fallback (open models).
    """

    @abc.abstractmethod
    def parse(self, *, system: str, user: str, schema: type[T]) -> T:
        """Run one call and return a validated instance of ``schema``."""
        raise NotImplementedError


class AnthropicBackend(LLMBackend):
    """Default backend — Claude with typed structured output and adaptive thinking.

    The Anthropic client is constructed lazily on first use, so importing this
    module (and the offline pipeline) never requires a configured API key.
    """

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 16000,
    ) -> None:
        self._client = client
        self.model = model
        self.max_tokens = max_tokens

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def parse(self, *, system: str, user: str, schema: type[T]) -> T:
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=self.max_tokens,
            thinking={"type": "adaptive"},
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user}],
            output_format=schema,
        )
        if response.parsed_output is None:
            raise RuntimeError(
                f"Failed to parse {schema.__name__} (stop_reason={response.stop_reason})"
            )
        return response.parsed_output
