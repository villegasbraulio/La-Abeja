"""Optional provider-backed response generator with deterministic fallback."""

from __future__ import annotations

from dataclasses import dataclass, field

from apps.ai.providers import LLMProvider, LLMProviderFactory


@dataclass(slots=True)
class LLMResponse:
    """Normalized response from the LLM service."""

    text: str
    model: str
    used_llm: bool
    metadata: dict[str, object] = field(default_factory=dict)


class LLMClient:
    """Generate grounded text responses if an LLM provider is configured."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        """Build the configured provider strategy lazily."""
        self.provider = provider or LLMProviderFactory.create()

    def generate_grounded_response(
        self,
        *,
        system_prompt: str,
        user_message: str,
        evidence: list[str],
        fallback_text: str,
    ) -> LLMResponse:
        """Use the configured provider when available, otherwise return the fallback text."""
        response = self.provider.generate_grounded_response(
            system_prompt=system_prompt,
            user_message=user_message,
            evidence=evidence,
        )
        if response is None:
            observation = getattr(self.provider, "last_observation", {})
            return LLMResponse(
                text=fallback_text,
                model="deterministic-fallback",
                used_llm=False,
                metadata=dict(observation) if isinstance(observation, dict) else {},
            )
        return LLMResponse(
            text=response.text,
            model=response.model,
            used_llm=True,
            metadata=response.metadata,
        )
