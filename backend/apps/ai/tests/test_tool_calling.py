"""Unit tests for the OpenAI-backed tool-calling layer."""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from apps.ai.agents.prompt_manager import PromptManager
from apps.ai.agents.tool_calling_agent import OpenAIToolCallingAgent
from apps.ai.models import AgentRun, Conversation, KnowledgeSource
from apps.ai.rag.ingest import KnowledgeIngestionService
from apps.ai.tools.base import ToolContext
from apps.ai.tools.registry import ToolRegistry


class _FakeFunctionCall:
    """Minimal fake function-call item returned by the Responses API."""

    type = "function_call"

    def __init__(self, name: str, arguments: dict[str, object], call_id: str) -> None:
        """Store fake tool call attributes."""
        self.name = name
        self.arguments = json.dumps(arguments)
        self.call_id = call_id


class _FakeResponse:
    """Minimal fake response envelope."""

    def __init__(
        self,
        *,
        response_id: str,
        output: list[object] | None = None,
        output_text: str = "",
    ) -> None:
        """Store fake response fields."""
        self.id = response_id
        self.output = output or []
        self.output_text = output_text


class _FakeResponsesAPI:
    """Queue-based fake Responses API."""

    def __init__(self, responses: list[_FakeResponse]) -> None:
        """Receive the ordered responses to replay."""
        self._responses = responses

    def create(self, **kwargs: object) -> _FakeResponse:
        """Pop the next canned response."""
        del kwargs
        return self._responses.pop(0)


class _FakeChatToolFunction:
    """Minimal chat-completions tool function payload."""

    def __init__(self, name: str, arguments: dict[str, object]) -> None:
        self.name = name
        self.arguments = json.dumps(arguments)


class _FakeChatToolCall:
    """Minimal chat-completions tool call payload."""

    def __init__(self, tool_id: str, name: str, arguments: dict[str, object]) -> None:
        self.id = tool_id
        self.function = _FakeChatToolFunction(name, arguments)


class _FakeChatMessage:
    """Minimal chat-completions assistant message."""

    def __init__(
        self,
        *,
        content: str | None = None,
        tool_calls: list[_FakeChatToolCall] | None = None,
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls or []


class _FakeChatChoice:
    """Minimal chat-completions choice payload."""

    def __init__(self, message: _FakeChatMessage) -> None:
        self.message = message


class _FakeChatCompletionResponse:
    """Minimal chat-completions response envelope."""

    def __init__(self, message: _FakeChatMessage) -> None:
        self.choices = [_FakeChatChoice(message)]


class _FakeChatCompletionsAPI:
    """Queue-based fake Chat Completions API."""

    def __init__(self, responses: list[_FakeChatCompletionResponse]) -> None:
        self._responses = responses

    def create(self, **kwargs: object) -> _FakeChatCompletionResponse:
        """Pop the next canned response."""
        del kwargs
        return self._responses.pop(0)


class _FakeOpenAIClient:
    """Minimal fake OpenAI client for tool-calling tests."""

    def __init__(
        self,
        *,
        api_key: str,
        responses: list[_FakeResponse] | None = None,
        chat_responses: list[_FakeChatCompletionResponse] | None = None,
        base_url: str | None = None,
    ) -> None:
        """Expose a fake responses API namespace."""
        del api_key, base_url
        self.responses = _FakeResponsesAPI(responses or [])
        self.chat = SimpleNamespace(completions=_FakeChatCompletionsAPI(chat_responses or []))


@pytest.fixture
def seeded_public_knowledge() -> KnowledgeSource:
    """Create a small public knowledge source for the knowledge tool."""
    source = KnowledgeSource.objects.create(
        name="Tool Calling KB",
        source_type=KnowledgeSource.SourceType.FAQ,
        uri="seed://tool-calling-kb",
    )
    KnowledgeIngestionService().upsert_document(
        source=source,
        external_id="pickup-policy",
        title="Retiro en bodega",
        content=(
            "El retiro en bodega se coordina luego de la confirmacion.\n"
            "Es ideal para combinar con una visita."
        ),
    )
    return source


@pytest.mark.django_db
def test_openai_tool_calling_agent_executes_registry_tools(
    settings,
    monkeypatch,
    seeded_public_knowledge,
) -> None:
    """The tool-calling agent should execute a tool and return the model's final answer."""
    del seeded_public_knowledge
    settings.AI_LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "test-key"
    settings.AI_USE_LLM = True
    settings.AI_USE_TOOL_CALLING = True

    fake_responses = [
        _FakeResponse(
            response_id="resp_1",
            output=[
                _FakeFunctionCall(
                    name="search_knowledge_base",
                    arguments={"query": "retiro en bodega"},
                    call_id="call_1",
                )
            ],
        ),
        _FakeResponse(
            response_id="resp_2",
            output=[],
            output_text="Sí, el retiro en bodega se coordina luego de la confirmación.",
        ),
    ]

    def fake_openai_factory(*, api_key: str) -> _FakeOpenAIClient:
        """Return a fake OpenAI client with queued responses."""
        return _FakeOpenAIClient(api_key=api_key, responses=list(fake_responses))

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=fake_openai_factory))

    conversation = Conversation.objects.create(mode=Conversation.Mode.SUPPORT)
    run = AgentRun.objects.create(conversation=conversation, agent_type=AgentRun.AgentType.SUPPORT)
    context = ToolContext(run=run, user_id=None, is_staff=False)

    result = OpenAIToolCallingAgent().run(
        message="Puedo retirar en bodega?",
        mode=Conversation.Mode.SUPPORT,
        context=context,
        tool_registry=ToolRegistry(),
        prompt=PromptManager().support_prompt(),
    )

    assert result is not None
    assert result.used_llm is True
    assert "retiro en bodega" in result.text.lower()
    assert result.metadata["executed_tools"] == ["search_knowledge_base"]
    assert len(result.citations) >= 1


@pytest.mark.django_db
def test_openai_tool_calling_agent_returns_none_when_disabled(settings) -> None:
    """The tool-calling layer should no-op cleanly when disabled."""
    settings.AI_LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = ""
    settings.AI_USE_LLM = False
    settings.AI_USE_TOOL_CALLING = False

    conversation = Conversation.objects.create(mode=Conversation.Mode.SUPPORT)
    run = AgentRun.objects.create(conversation=conversation, agent_type=AgentRun.AgentType.SUPPORT)
    context = ToolContext(run=run, user_id=None, is_staff=False)

    result = OpenAIToolCallingAgent().run(
        message="hola",
        mode=Conversation.Mode.SUPPORT,
        context=context,
        tool_registry=ToolRegistry(),
        prompt=PromptManager().support_prompt(),
    )

    assert result is None


@pytest.mark.django_db
def test_tool_calling_agent_supports_groq_with_openai_compatible_sdk(
    settings,
    monkeypatch,
    seeded_public_knowledge,
) -> None:
    """Groq should use the OpenAI-compatible chat completions path for local tools."""
    del seeded_public_knowledge
    settings.AI_LLM_PROVIDER = "groq"
    settings.GROQ_API_KEY = "groq-test-key"
    settings.GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    settings.AI_CHAT_MODEL = "openai/gpt-oss-20b"
    settings.AI_USE_LLM = True
    settings.AI_USE_TOOL_CALLING = True
    captured: dict[str, str | None] = {}

    fake_chat_responses = [
        _FakeChatCompletionResponse(
            _FakeChatMessage(
                tool_calls=[
                    _FakeChatToolCall(
                        tool_id="call_1",
                        name="search_knowledge_base",
                        arguments={"query": "retiro en bodega"},
                    )
                ]
            )
        ),
        _FakeChatCompletionResponse(
            _FakeChatMessage(content="Groq tambien resolvio el retiro en bodega.")
        ),
    ]

    def fake_openai_factory(*, api_key: str, base_url: str | None = None) -> _FakeOpenAIClient:
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        return _FakeOpenAIClient(
            api_key=api_key,
            base_url=base_url,
            chat_responses=list(fake_chat_responses),
        )

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=fake_openai_factory))

    conversation = Conversation.objects.create(mode=Conversation.Mode.SUPPORT)
    run = AgentRun.objects.create(conversation=conversation, agent_type=AgentRun.AgentType.SUPPORT)
    context = ToolContext(run=run, user_id=None, is_staff=False)

    result = OpenAIToolCallingAgent().run(
        message="Puedo retirar en bodega?",
        mode=Conversation.Mode.SUPPORT,
        context=context,
        tool_registry=ToolRegistry(),
        prompt=PromptManager().support_prompt(),
    )

    assert result is not None
    assert result.used_llm is True
    assert "retiro en bodega" in result.text.lower()
    assert result.metadata["executed_tools"] == ["search_knowledge_base"]
    assert captured == {
        "api_key": "groq-test-key",
        "base_url": "https://api.groq.com/openai/v1",
    }


@pytest.mark.django_db
def test_tool_calling_agent_supports_groq_unknown_tools_without_crashing(
    settings,
    monkeypatch,
) -> None:
    """Groq chat-completions tool loops should tolerate unknown tool names."""
    settings.AI_LLM_PROVIDER = "groq"
    settings.GROQ_API_KEY = "groq-test-key"
    settings.GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    settings.AI_CHAT_MODEL = "openai/gpt-oss-20b"
    settings.AI_USE_LLM = True
    settings.AI_USE_TOOL_CALLING = True

    fake_chat_responses = [
        _FakeChatCompletionResponse(
            _FakeChatMessage(
                tool_calls=[
                    _FakeChatToolCall(
                        tool_id="call_1",
                        name="unknown_tool",
                        arguments={"query": "retiro en bodega"},
                    )
                ]
            )
        ),
        _FakeChatCompletionResponse(_FakeChatMessage(content="Skipped unknown tool.")),
    ]

    def fake_openai_factory(*, api_key: str, base_url: str | None = None) -> _FakeOpenAIClient:
        return _FakeOpenAIClient(
            api_key=api_key,
            base_url=base_url,
            chat_responses=list(fake_chat_responses),
        )

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=fake_openai_factory))

    conversation = Conversation.objects.create(mode=Conversation.Mode.SUPPORT)
    run = AgentRun.objects.create(conversation=conversation, agent_type=AgentRun.AgentType.SUPPORT)
    context = ToolContext(run=run, user_id=None, is_staff=False)

    result = OpenAIToolCallingAgent().run(
        message="hola",
        mode=Conversation.Mode.SUPPORT,
        context=context,
        tool_registry=ToolRegistry(),
        prompt=PromptManager().support_prompt(),
    )

    assert result is not None
    assert result.text == "Skipped unknown tool."
    assert result.metadata["executed_tools"] == []
