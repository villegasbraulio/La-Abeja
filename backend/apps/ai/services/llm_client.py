"""Optional OpenAI-backed response generator with deterministic fallback."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass(slots=True)
class LLMResponse:
    """Normalized response from the LLM service."""

    text: str
    model: str
    used_llm: bool


class LLMClient:
    """Generate grounded text responses if OpenAI is configured."""

    def generate_grounded_response(
        self,
        *,
        system_prompt: str,
        user_message: str,
        evidence: list[str],
        fallback_text: str,
    ) -> LLMResponse:
        """Use OpenAI when available, otherwise return the fallback text."""
        if not settings.AI_USE_LLM or not settings.OPENAI_API_KEY:
            return LLMResponse(text=fallback_text, model="deterministic-fallback", used_llm=False)

        try:
            from openai import OpenAI
        except ImportError:
            return LLMResponse(text=fallback_text, model="deterministic-fallback", used_llm=False)

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.responses.create(
                model=settings.AI_CHAT_MODEL,
                input=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"User message:\n{user_message}\n\n"
                            f"Grounding evidence:\n- " + "\n- ".join(evidence)
                        ),
                    },
                ],
            )
            output_text = getattr(response, "output_text", "").strip()
            if output_text:
                return LLMResponse(
                    text=output_text,
                    model=settings.AI_CHAT_MODEL,
                    used_llm=True,
                )
        except Exception:
            return LLMResponse(text=fallback_text, model="deterministic-fallback", used_llm=False)

        return LLMResponse(text=fallback_text, model="deterministic-fallback", used_llm=False)
