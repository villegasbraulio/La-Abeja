"""Factory for selecting the active LLM provider strategy."""

from __future__ import annotations

from django.conf import settings

from apps.ai.providers.base import LLMProvider, NullLLMProvider
from apps.ai.providers.openai_compatible import (
    OpenAICompatibleProvider,
    OpenAICompatibleProviderConfig,
)

GROQ_DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"


class LLMProviderFactory:
    """Instantiate the configured LLM provider strategy."""

    @classmethod
    def create(cls) -> LLMProvider:
        """Build the configured provider or a safe no-op fallback."""
        if not settings.AI_USE_LLM:
            return NullLLMProvider()

        provider_name = (
            str(getattr(settings, "AI_LLM_PROVIDER", "openai")).strip().lower() or "openai"
        )
        if provider_name == "openai":
            if not settings.OPENAI_API_KEY:
                return NullLLMProvider(provider_name="openai")
            return OpenAICompatibleProvider(
                OpenAICompatibleProviderConfig(
                    provider_name="openai",
                    api_key=settings.OPENAI_API_KEY,
                    model=settings.AI_CHAT_MODEL,
                )
            )

        if provider_name == "groq":
            groq_api_key = str(getattr(settings, "GROQ_API_KEY", "")).strip()
            if not groq_api_key:
                return NullLLMProvider(provider_name="groq")
            groq_base_url = str(getattr(settings, "GROQ_BASE_URL", GROQ_DEFAULT_BASE_URL)).strip()
            return OpenAICompatibleProvider(
                OpenAICompatibleProviderConfig(
                    provider_name="groq",
                    api_key=groq_api_key,
                    model=settings.AI_CHAT_MODEL,
                    base_url=groq_base_url or GROQ_DEFAULT_BASE_URL,
                )
            )

        return NullLLMProvider(provider_name=f"unsupported:{provider_name}")
