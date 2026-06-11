"""Edge-case tests for the OpenAI tool-calling and orchestration loop."""

# ruff: noqa: E501

from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from apps.ai.agents.orchestrator import AIOrchestrator
from apps.ai.agents.prompt_manager import PromptManager
from apps.ai.agents.tool_calling_agent import OpenAIToolCallingAgent
from apps.ai.models import AgentRun, Conversation, KnowledgeSource, ToolExecution
from apps.ai.rag.ingest import KnowledgeIngestionService
from apps.ai.tools.base import ToolContext
from apps.ai.tools.registry import ToolRegistry
from apps.authentication.tests.factories import UserFactory
from apps.catalog.tests.factories import WineFactory
from apps.orders.models import Order
from apps.orders.tests.factories import OrderFactory


class _FakeFunctionCall:
    """Minimal fake function-call item returned by the Responses API."""

    type = "function_call"

    def __init__(self, name: str, arguments: object, call_id: str) -> None:
        self.name = name
        self.arguments = arguments
        self.call_id = call_id


class _FakeResponse:
    """Minimal fake response envelope."""

    def __init__(
        self, *, response_id: str, output: list[object] | None = None, output_text: str = ""
    ) -> None:
        self.id = response_id
        self.output = output or []
        self.output_text = output_text


class _QueueResponsesAPI:
    """Queue-based fake Responses API."""

    def __init__(self, responses: list[_FakeResponse], *, should_raise: bool = False) -> None:
        self._responses = responses
        self._should_raise = should_raise

    def create(self, **kwargs: object) -> _FakeResponse:
        del kwargs
        if self._should_raise:
            raise RuntimeError("responses exploded")
        return self._responses.pop(0)


class _FakeOpenAIClient:
    """Minimal fake OpenAI client for tool-calling tests."""

    def __init__(
        self, *, api_key: str, responses: list[_FakeResponse], should_raise: bool = False
    ) -> None:
        del api_key
        self.responses = _QueueResponsesAPI(responses=list(responses), should_raise=should_raise)


@pytest.fixture
def seeded_catalog_and_knowledge() -> None:
    """Seed one wine and one public knowledge document for tool-calling tests."""
    WineFactory(name="Malbec Tool Eval", sku="TOOL-EVAL-MAL")
    source = KnowledgeSource.objects.create(
        name="Tool Calling Edge KB",
        source_type=KnowledgeSource.SourceType.FAQ,
        uri="seed://tool-calling-edge-kb",
    )
    KnowledgeIngestionService().upsert_document(
        source=source,
        external_id="pickup-policy",
        title="Retiro en bodega",
        content="El retiro en bodega se coordina luego de la confirmacion.",
    )


def _context(mode: str = Conversation.Mode.SUPPORT, *, is_staff: bool = False) -> ToolContext:
    """Create a run context for the agent layer."""
    user = UserFactory(is_staff=is_staff)
    conversation = Conversation.objects.create(mode=mode, customer=user)
    run = AgentRun.objects.create(
        conversation=conversation,
        agent_type=AgentRun.AgentType.OPS if is_staff else AgentRun.AgentType.SUPPORT,
    )
    return ToolContext(run=run, user_id=str(user.id), is_staff=is_staff)


@pytest.mark.django_db
def test_tool_calling_agent_executes_multiple_tools_in_order(
    settings, monkeypatch, seeded_catalog_and_knowledge
) -> None:
    """Multiple tool calls should execute sequentially and preserve order metadata."""
    del seeded_catalog_and_knowledge
    settings.AI_LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "test-key"
    settings.AI_USE_LLM = True
    settings.AI_USE_TOOL_CALLING = True
    responses = [
        _FakeResponse(
            response_id="resp-1",
            output=[
                _FakeFunctionCall("search_catalog", json.dumps({"query": "Malbec"}), "call-1"),
                _FakeFunctionCall(
                    "search_knowledge_base", json.dumps({"query": "retiro en bodega"}), "call-2"
                ),
            ],
        ),
        _FakeResponse(response_id="resp-2", output=[], output_text="Use dos tools."),
    ]
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(
            OpenAI=lambda *, api_key: _FakeOpenAIClient(api_key=api_key, responses=responses)
        ),
    )

    result = OpenAIToolCallingAgent().run(
        message="Buscame un Malbec y decime si hay retiro en bodega",
        mode=Conversation.Mode.SUPPORT,
        context=_context(),
        tool_registry=ToolRegistry(),
        prompt=PromptManager().support_prompt(),
    )

    assert result is not None
    assert result.metadata["executed_tools"] == ["search_catalog", "search_knowledge_base"]
    assert len(result.citations) >= 1


@pytest.mark.django_db
def test_tool_calling_agent_handles_invalid_json_arguments(
    settings, monkeypatch, seeded_catalog_and_knowledge
) -> None:
    """Invalid JSON arguments should not crash the tool loop."""
    del seeded_catalog_and_knowledge
    settings.AI_LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "test-key"
    settings.AI_USE_LLM = True
    settings.AI_USE_TOOL_CALLING = True
    responses = [
        _FakeResponse(
            response_id="resp-1",
            output=[_FakeFunctionCall("search_knowledge_base", "{bad-json", "call-1")],
        ),
        _FakeResponse(response_id="resp-2", output=[], output_text="No crash."),
    ]
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(
            OpenAI=lambda *, api_key: _FakeOpenAIClient(api_key=api_key, responses=responses)
        ),
    )

    result = OpenAIToolCallingAgent().run(
        message="hola",
        mode=Conversation.Mode.SUPPORT,
        context=_context(),
        tool_registry=ToolRegistry(),
        prompt=PromptManager().support_prompt(),
    )

    assert result is not None
    assert result.text == "No crash."
    assert result.metadata["executed_tools"] == ["search_knowledge_base"]


@pytest.mark.django_db
def test_tool_calling_agent_ignores_unknown_tools_and_finishes(settings, monkeypatch) -> None:
    """Unknown tool names should be skipped rather than blowing up the loop."""
    settings.AI_LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "test-key"
    settings.AI_USE_LLM = True
    settings.AI_USE_TOOL_CALLING = True
    responses = [
        _FakeResponse(
            response_id="resp-1",
            output=[_FakeFunctionCall("nonexistent_tool", json.dumps({"x": 1}), "call-1")],
        ),
        _FakeResponse(response_id="resp-2", output=[], output_text="Skipped unknown tool."),
    ]
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(
            OpenAI=lambda *, api_key: _FakeOpenAIClient(api_key=api_key, responses=responses)
        ),
    )

    result = OpenAIToolCallingAgent().run(
        message="hola",
        mode=Conversation.Mode.SUPPORT,
        context=_context(),
        tool_registry=ToolRegistry(),
        prompt=PromptManager().support_prompt(),
    )

    assert result is not None
    assert result.text == "Skipped unknown tool."
    assert result.metadata["executed_tools"] == []


@pytest.mark.django_db
def test_tool_calling_agent_returns_none_on_empty_final_output(settings, monkeypatch) -> None:
    """Blank model outputs should degrade to the orchestrator fallback path."""
    settings.AI_LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "test-key"
    settings.AI_USE_LLM = True
    settings.AI_USE_TOOL_CALLING = True
    responses = [_FakeResponse(response_id="resp-1", output=[], output_text="   ")]
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(
            OpenAI=lambda *, api_key: _FakeOpenAIClient(api_key=api_key, responses=responses)
        ),
    )

    result = OpenAIToolCallingAgent().run(
        message="hola",
        mode=Conversation.Mode.SUPPORT,
        context=_context(),
        tool_registry=ToolRegistry(),
        prompt=PromptManager().support_prompt(),
    )

    assert result is None


@pytest.mark.django_db
def test_orchestrator_marks_run_for_human_when_llm_requests_blocked_write(
    settings, monkeypatch
) -> None:
    """Tool-calling runs should surface pending approvals instead of pretending the write happened."""
    settings.AI_LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "test-key"
    settings.AI_USE_LLM = True
    settings.AI_USE_TOOL_CALLING = True
    staff_user = UserFactory(is_staff=True)
    order = OrderFactory(
        user=UserFactory(), order_number="LAB-2026-000811", status=Order.Status.READY_TO_SHIP
    )
    responses = [
        _FakeResponse(
            response_id="resp-1",
            output=[
                _FakeFunctionCall(
                    "update_order_status",
                    json.dumps(
                        {
                            "order_number": order.order_number,
                            "new_status": "shipped",
                            "tracking_number": "AND-811",
                        }
                    ),
                    "call-1",
                )
            ],
        ),
        _FakeResponse(
            response_id="resp-2",
            output=[],
            output_text="La accion fue preparada y quedo pendiente de aprobacion.",
        ),
    ]
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(
            OpenAI=lambda *, api_key: _FakeOpenAIClient(api_key=api_key, responses=responses)
        ),
    )

    conversation = Conversation.objects.create(mode=Conversation.Mode.OPS, customer=staff_user)
    result = AIOrchestrator().handle_message(
        conversation=conversation,
        message=f"Marca el pedido {order.order_number} como enviado",
        user_id=str(staff_user.id),
        is_staff=True,
    )

    result.run.refresh_from_db()
    assert result.run.needs_human is True
    assert result.run.metadata["pending_approval_ids"]
    assert "pendiente de aprobacion" in result.assistant_turn.content.lower()
    assert ToolExecution.objects.filter(
        run=result.run,
        tool_name="update_order_status",
        status=ToolExecution.Status.BLOCKED,
    ).exists()


@pytest.mark.django_db
def test_tool_calling_agent_returns_none_on_openai_exception(settings, monkeypatch) -> None:
    """Unexpected OpenAI errors should not bubble up to callers."""
    settings.AI_LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "test-key"
    settings.AI_USE_LLM = True
    settings.AI_USE_TOOL_CALLING = True
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(
            OpenAI=lambda *, api_key: _FakeOpenAIClient(
                api_key=api_key, responses=[], should_raise=True
            )
        ),
    )

    result = OpenAIToolCallingAgent().run(
        message="hola",
        mode=Conversation.Mode.SUPPORT,
        context=_context(),
        tool_registry=ToolRegistry(),
        prompt=PromptManager().support_prompt(),
    )

    assert result is None
