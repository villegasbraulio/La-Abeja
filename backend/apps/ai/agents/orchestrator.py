"""Conversation orchestrator for the AI app."""

from __future__ import annotations

import re
from dataclasses import dataclass

from django.db import transaction

from apps.ai.agents.prompt_manager import PromptManager
from apps.ai.agents.response_builder import ResponseBuilder
from apps.ai.models import AgentRun, Conversation, ConversationTurn
from apps.ai.services.llm_client import LLMClient
from apps.ai.tools.base import ToolContext
from apps.ai.tools.registry import ToolRegistry

ORDER_NUMBER_RE = re.compile(r"LAB-\d{4}-\d{3,}", re.IGNORECASE)


@dataclass(slots=True)
class OrchestratorResult:
    """Normalized result from a handled message."""

    assistant_turn: ConversationTurn
    run: AgentRun


class AIOrchestrator:
    """Route a conversation turn through retrieval and tools."""

    def __init__(self) -> None:
        """Create helper services."""
        self.tool_registry = ToolRegistry()
        self.prompt_manager = PromptManager()
        self.response_builder = ResponseBuilder()
        self.llm_client = LLMClient()

    @transaction.atomic
    def handle_message(
        self,
        *,
        conversation: Conversation,
        message: str,
        user_id: str | None,
        is_staff: bool,
    ) -> OrchestratorResult:
        """Persist the user message, run the orchestration, and store the assistant reply."""
        user_turn = ConversationTurn.objects.create(
            conversation=conversation,
            role=ConversationTurn.Role.USER,
            content=message,
        )
        del user_turn
        agent_type = AgentRun.AgentType.OPS if conversation.mode == Conversation.Mode.OPS else AgentRun.AgentType.SUPPORT
        run = AgentRun.objects.create(
            conversation=conversation,
            agent_type=agent_type,
            intent="",
            message_text=message,
        )
        context = ToolContext(run=run, user_id=user_id, is_staff=is_staff)
        intent, payload = self._detect_intent(message=message, is_staff=is_staff)
        conversation.last_intent = intent
        conversation.save(update_fields=["last_intent", "updated_at"])
        run.intent = intent

        if intent == "order_status":
            result = self.tool_registry.execute(tool_name="get_order_by_number", payload=payload, context=context)
            fallback_text = self.response_builder.build_order_status_response(result)
            evidence = [f"tool:get_order_by_number:{result.get('order_number', '')}"]
            citations: list[dict[str, object]] = []
        elif intent == "low_stock":
            result = self.tool_registry.execute(tool_name="list_low_stock_items", payload=payload, context=context)
            fallback_text = self.response_builder.build_low_stock_response(result.get("results", []))
            evidence = ["tool:list_low_stock_items"]
            citations = []
        elif intent == "pending_orders":
            result = self.tool_registry.execute(tool_name="list_pending_orders", payload=payload, context=context)
            fallback_text = self.response_builder.build_pending_orders_response(result.get("results", []))
            evidence = ["tool:list_pending_orders"]
            citations = []
        elif intent == "catalog_search":
            result = self.tool_registry.execute(tool_name="search_catalog", payload=payload, context=context)
            fallback_text = self.response_builder.build_catalog_response(result.get("results", []))
            evidence = ["tool:search_catalog"]
            citations = []
        else:
            result = self.tool_registry.execute(
                tool_name="search_knowledge_base",
                payload={"query": message},
                context=context,
            )
            kb_results = list(result.get("results", []))
            fallback_text = self.response_builder.build_knowledge_response(kb_results)
            evidence = [
                f"{item.get('document_title', 'knowledge')}::{item.get('section', '')}"
                for item in kb_results[:3]
            ]
            citations = [
                {
                    "chunk_id": item.get("chunk_id"),
                    "document_id": item.get("document_id"),
                    "document_title": item.get("document_title"),
                    "section": item.get("section"),
                }
                for item in kb_results[:3]
            ]

        llm_response = self.llm_client.generate_grounded_response(
            system_prompt=(
                self.prompt_manager.ops_prompt()
                if conversation.mode == Conversation.Mode.OPS
                else self.prompt_manager.support_prompt()
            ),
            user_message=message,
            evidence=evidence,
            fallback_text=fallback_text,
        )
        assistant_turn = ConversationTurn.objects.create(
            conversation=conversation,
            role=ConversationTurn.Role.ASSISTANT,
            content=llm_response.text,
            citations=citations,
            metadata={"intent": intent, "used_llm": llm_response.used_llm, "model": llm_response.model},
        )

        run.model = llm_response.model
        run.status = AgentRun.Status.COMPLETED
        run.response_text = assistant_turn.content
        run.citations = citations
        run.confidence = 0.950 if intent != "knowledge_search" else (0.880 if citations else 0.350)
        run.needs_human = not citations and intent == "knowledge_search"
        run.metadata = {"tool_payload": payload, "used_llm": llm_response.used_llm}
        run.save(
            update_fields=[
                "intent",
                "model",
                "status",
                "response_text",
                "citations",
                "confidence",
                "needs_human",
                "metadata",
                "updated_at",
            ]
        )
        conversation.summary = assistant_turn.content[:500]
        conversation.save(update_fields=["summary", "updated_at"])
        return OrchestratorResult(assistant_turn=assistant_turn, run=run)

    def _detect_intent(self, *, message: str, is_staff: bool) -> tuple[str, dict[str, object]]:
        """Infer a narrow intent from the message using business heuristics."""
        normalized = message.lower()
        order_match = ORDER_NUMBER_RE.search(message)
        if order_match:
            return "order_status", {"order_number": order_match.group(0).upper()}
        if is_staff and "stock" in normalized:
            return "low_stock", {"limit": 5}
        if is_staff and ("pendiente" in normalized or "preparando" in normalized) and "pedido" in normalized:
            return "pending_orders", {"limit": 5}
        if any(keyword in normalized for keyword in ["vino", "malbec", "cabernet", "blend", "etiqueta"]):
            return "catalog_search", {"query": message}
        return "knowledge_search", {}
