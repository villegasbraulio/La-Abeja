"""Provider-backed tool-calling agent."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from apps.ai.providers import LLMProvider, LLMProviderFactory
from apps.ai.tools.base import ToolContext
from apps.ai.tools.registry import ToolRegistry


@dataclass(slots=True)
class ToolCallingAgentResult:
    """Normalized result from a tool-calling run."""

    text: str
    model: str
    used_llm: bool
    citations: list[dict[str, object]]
    metadata: dict[str, object]


class ToolCallingAgent:
    """Run a multi-step tool loop through the configured provider."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        """Build the configured provider strategy lazily."""
        self.provider = provider or LLMProviderFactory.create()

    def run(
        self,
        *,
        message: str,
        mode: str,
        context: ToolContext,
        tool_registry: ToolRegistry,
        prompt: str,
    ) -> ToolCallingAgentResult | None:
        """Attempt a tool-calling conversation and return the final text."""
        if not settings.AI_USE_LLM or not settings.AI_USE_TOOL_CALLING:
            return None

        result = self.provider.run_tool_calling(
            message=message,
            mode=mode,
            context=context,
            tool_registry=tool_registry,
            prompt=prompt,
        )
        if result is None:
            return None
        return ToolCallingAgentResult(
            text=result.text,
            model=result.model,
            used_llm=True,
            citations=result.citations,
            metadata=result.metadata,
        )


OpenAIToolCallingAgent = ToolCallingAgent
