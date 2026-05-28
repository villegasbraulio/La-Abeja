"""Provider abstractions for external LLM backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from apps.ai.tools.base import ToolContext
from apps.ai.tools.registry import ToolRegistry


@dataclass(slots=True)
class ProviderTextResponse:
    """Normalized text response from a remote LLM provider."""

    text: str
    model: str


@dataclass(slots=True)
class ProviderToolCallResult:
    """Normalized result from a remote tool-calling run."""

    text: str
    model: str
    citations: list[dict[str, object]]
    metadata: dict[str, object]


class LLMProvider(ABC):
    """Strategy interface for chat-capable LLM providers."""

    provider_name: str

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when the provider can be used."""

    @abstractmethod
    def generate_grounded_response(
        self,
        *,
        system_prompt: str,
        user_message: str,
        evidence: list[str],
    ) -> ProviderTextResponse | None:
        """Generate a grounded response using the provider."""

    @abstractmethod
    def run_tool_calling(
        self,
        *,
        message: str,
        mode: str,
        context: ToolContext,
        tool_registry: ToolRegistry,
        prompt: str,
    ) -> ProviderToolCallResult | None:
        """Run the local tool-calling loop through the provider."""


@dataclass(slots=True)
class NullLLMProvider(LLMProvider):
    """No-op provider used for disabled or unsupported configurations."""

    provider_name: str = "disabled"

    def is_available(self) -> bool:
        """A null provider is never available."""
        return False

    def generate_grounded_response(
        self,
        *,
        system_prompt: str,
        user_message: str,
        evidence: list[str],
    ) -> ProviderTextResponse | None:
        """Return no remote response."""
        del system_prompt, user_message, evidence
        return None

    def run_tool_calling(
        self,
        *,
        message: str,
        mode: str,
        context: ToolContext,
        tool_registry: ToolRegistry,
        prompt: str,
    ) -> ProviderToolCallResult | None:
        """Return no remote tool-calling result."""
        del message, mode, context, tool_registry, prompt
        return None
