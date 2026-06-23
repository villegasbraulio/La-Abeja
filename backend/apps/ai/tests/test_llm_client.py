"""Unit tests for the grounded LLM client wrapper."""

from __future__ import annotations

import sys
from types import SimpleNamespace

from apps.ai.services.llm_client import LLMClient


class _FakeResponse:
    """Minimal fake response object with only output_text."""

    def __init__(self, output_text: str, usage: object | None = None) -> None:
        self.output_text = output_text
        self.usage = usage


class _FakeResponsesAPI:
    """Fake Responses API namespace."""

    def __init__(self, *, output_text: str = "", should_raise: bool = False) -> None:
        self.output_text = output_text
        self.should_raise = should_raise

    def create(self, **kwargs: object) -> _FakeResponse:
        """Return a fake response or raise to simulate API failures."""
        del kwargs
        if self.should_raise:
            raise RuntimeError("boom")
        return _FakeResponse(self.output_text)


class _FakeOpenAIClient:
    """Minimal fake OpenAI client with a fake responses namespace."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        output_text: str = "",
        should_raise: bool = False,
    ) -> None:
        del api_key, base_url
        self.responses = _FakeResponsesAPI(output_text=output_text, should_raise=should_raise)


class _RetryingResponsesAPI:
    """Fail once with a transient error and then return a metered response."""

    def __init__(self) -> None:
        self.call_count = 0

    def create(self, **kwargs: object) -> _FakeResponse:
        del kwargs
        self.call_count += 1
        if self.call_count == 1:
            raise TimeoutError("temporary timeout")
        return _FakeResponse(
            "Respuesta luego del retry",
            usage=SimpleNamespace(input_tokens=120, output_tokens=30, total_tokens=150),
        )


def test_llm_client_returns_fallback_when_disabled(settings) -> None:
    """No API key or disabled flag should force deterministic fallback."""
    settings.AI_LLM_PROVIDER = "openai"
    settings.AI_USE_LLM = False
    settings.OPENAI_API_KEY = ""

    result = LLMClient().generate_grounded_response(
        system_prompt="system",
        user_message="hola",
        evidence=["doc"],
        fallback_text="fallback",
    )

    assert result.text == "fallback"
    assert result.model == "deterministic-fallback"
    assert result.used_llm is False


def test_llm_client_returns_fallback_on_import_error(settings, monkeypatch) -> None:
    """Import errors should not break the agent path."""
    settings.AI_LLM_PROVIDER = "openai"
    settings.AI_USE_LLM = True
    settings.OPENAI_API_KEY = "test-key"
    monkeypatch.delitem(sys.modules, "openai", raising=False)

    original_import = __import__

    def failing_import(name: str, *args: object, **kwargs: object):
        if name == "openai":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", failing_import)

    result = LLMClient().generate_grounded_response(
        system_prompt="system",
        user_message="hola",
        evidence=["doc"],
        fallback_text="fallback",
    )

    assert result.text == "fallback"
    assert result.used_llm is False


def test_llm_client_returns_fallback_on_api_exception(settings, monkeypatch) -> None:
    """Remote API exceptions should degrade to deterministic fallback."""
    settings.AI_LLM_PROVIDER = "openai"
    settings.AI_USE_LLM = True
    settings.OPENAI_API_KEY = "test-key"
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(
            OpenAI=lambda *, api_key: _FakeOpenAIClient(api_key=api_key, should_raise=True)
        ),
    )

    result = LLMClient().generate_grounded_response(
        system_prompt="system",
        user_message="hola",
        evidence=["doc"],
        fallback_text="fallback",
    )

    assert result.text == "fallback"
    assert result.used_llm is False
    observation = result.metadata["provider_observability"]
    assert observation["fallback_reason"] == "provider_exception"
    assert observation["error_type"] == "RuntimeError"


def test_llm_client_returns_fallback_on_empty_output(settings, monkeypatch) -> None:
    """Empty model responses should not leak through as blank assistant replies."""
    settings.AI_LLM_PROVIDER = "openai"
    settings.AI_USE_LLM = True
    settings.OPENAI_API_KEY = "test-key"
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(
            OpenAI=lambda *, api_key: _FakeOpenAIClient(
                api_key=api_key,
                output_text="   ",
            )
        ),
    )

    result = LLMClient().generate_grounded_response(
        system_prompt="system",
        user_message="hola",
        evidence=["doc"],
        fallback_text="fallback",
    )

    assert result.text == "fallback"
    assert result.used_llm is False


def test_llm_client_returns_model_text_when_openai_succeeds(settings, monkeypatch) -> None:
    """Successful remote responses should be surfaced with the configured model."""
    settings.AI_LLM_PROVIDER = "openai"
    settings.AI_USE_LLM = True
    settings.OPENAI_API_KEY = "test-key"
    settings.AI_CHAT_MODEL = "gpt-test"
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(
            OpenAI=lambda *, api_key: _FakeOpenAIClient(
                api_key=api_key,
                output_text="Respuesta remota",
            )
        ),
    )

    result = LLMClient().generate_grounded_response(
        system_prompt="system",
        user_message="hola",
        evidence=["doc"],
        fallback_text="fallback",
    )

    assert result.text == "Respuesta remota"
    assert result.model == "gpt-test"
    assert result.used_llm is True


def test_llm_client_records_tokens_cost_latency_and_retries(settings, monkeypatch) -> None:
    """Successful calls should expose metering and bounded retry telemetry."""
    settings.AI_LLM_PROVIDER = "openai"
    settings.AI_USE_LLM = True
    settings.OPENAI_API_KEY = "test-key"
    settings.AI_CHAT_MODEL = "gpt-test"
    settings.AI_PROVIDER_MAX_RETRIES = 2
    settings.AI_PROVIDER_RETRY_BASE_SECONDS = 0
    settings.AI_INPUT_COST_PER_1M_TOKENS_USD = 2.0
    settings.AI_OUTPUT_COST_PER_1M_TOKENS_USD = 8.0
    responses_api = _RetryingResponsesAPI()
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(
            OpenAI=lambda *, api_key: SimpleNamespace(responses=responses_api),
        ),
    )

    result = LLMClient().generate_grounded_response(
        system_prompt="system",
        user_message="hola",
        evidence=["doc"],
        fallback_text="fallback",
    )

    observation = result.metadata["provider_observability"]
    assert result.used_llm is True
    assert responses_api.call_count == 2
    assert observation["retry_count"] == 1
    assert observation["token_usage"] == {
        "input_tokens": 120,
        "output_tokens": 30,
        "total_tokens": 150,
    }
    assert observation["estimated_cost_usd"] == 0.00048
    assert observation["latency_ms"] >= 0


def test_llm_client_supports_groq_with_openai_compatible_sdk(settings, monkeypatch) -> None:
    """Groq should be reachable through the same OpenAI SDK with a custom base URL."""
    settings.AI_USE_LLM = True
    settings.AI_LLM_PROVIDER = "groq"
    settings.GROQ_API_KEY = "groq-test-key"
    settings.GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    settings.AI_CHAT_MODEL = "openai/gpt-oss-20b"
    captured: dict[str, str | None] = {}

    def fake_openai_factory(*, api_key: str, base_url: str | None = None) -> _FakeOpenAIClient:
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        return _FakeOpenAIClient(
            api_key=api_key,
            base_url=base_url,
            output_text="Respuesta desde Groq",
        )

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=fake_openai_factory))

    result = LLMClient().generate_grounded_response(
        system_prompt="system",
        user_message="hola",
        evidence=["doc"],
        fallback_text="fallback",
    )

    assert result.text == "Respuesta desde Groq"
    assert result.model == "openai/gpt-oss-20b"
    assert result.used_llm is True
    assert captured == {
        "api_key": "groq-test-key",
        "base_url": "https://api.groq.com/openai/v1",
    }
