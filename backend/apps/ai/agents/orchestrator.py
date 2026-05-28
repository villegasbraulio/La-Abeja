"""Conversation orchestrator for the AI app."""

from __future__ import annotations

import re
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.ai.agents.prompt_manager import PromptManager
from apps.ai.agents.response_builder import ResponseBuilder
from apps.ai.agents.tool_calling_agent import ToolCallingAgent
from apps.ai.models import AgentRun, Conversation, ConversationTurn
from apps.ai.services.llm_client import LLMClient
from apps.ai.tools.base import ToolContext
from apps.ai.tools.registry import ToolRegistry

ORDER_NUMBER_RE = re.compile(r"LAB-\d{4}-\d{3,}", re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.IGNORECASE)
TRACKING_RE = re.compile(r"tracking(?:\s+numero)?[:\s]+([A-Z0-9-]+)", re.IGNORECASE)


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
        self.tool_calling_agent = ToolCallingAgent()

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

        prompt = (
            self.prompt_manager.ops_prompt()
            if conversation.mode == Conversation.Mode.OPS
            else self.prompt_manager.support_prompt()
        )
        tool_calling_result = self.tool_calling_agent.run(
            message=message,
            mode=conversation.mode,
            context=context,
            tool_registry=self.tool_registry,
            prompt=prompt,
        )
        if tool_calling_result is not None:
            has_pending_approvals = bool(run.metadata.get("pending_approval_ids"))
            assistant_turn = ConversationTurn.objects.create(
                conversation=conversation,
                role=ConversationTurn.Role.ASSISTANT,
                content=tool_calling_result.text,
                citations=tool_calling_result.citations,
                metadata={
                    "intent": intent,
                    "used_llm": tool_calling_result.used_llm,
                    "model": tool_calling_result.model,
                    **tool_calling_result.metadata,
                },
            )
            run.model = tool_calling_result.model
            run.status = AgentRun.Status.COMPLETED
            run.response_text = assistant_turn.content
            run.citations = tool_calling_result.citations
            run.confidence = 0.940
            run.needs_human = has_pending_approvals
            run.metadata = {
                **run.metadata,
                "tool_payload": payload,
                "used_llm": tool_calling_result.used_llm,
                **tool_calling_result.metadata,
            }
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

        if intent == "create_support_task":
            result = self.tool_registry.execute(tool_name="create_support_task", payload=payload, context=context)
            fallback_text = self.response_builder.build_support_task_response(result)
            evidence = [f"tool:create_support_task:{result.get('task_id', '')}"]
            citations: list[dict[str, object]] = []
        elif intent == "update_order_status":
            result = self.tool_registry.execute(tool_name="update_order_status", payload=payload, context=context)
            fallback_text = self.response_builder.build_order_status_update_response(result)
            evidence = [f"tool:update_order_status:{result.get('order_number', '')}"]
            citations = []
        elif intent == "order_status":
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
        elif intent == "payment_issue":
            result = self.tool_registry.execute(tool_name="check_payment_issue", payload=payload, context=context)
            fallback_text = self.response_builder.build_payment_issue_response(result)
            evidence = [f"tool:check_payment_issue:{result.get('order_number', '')}"]
            citations = []
        elif intent == "sales_summary":
            result = self.tool_registry.execute(tool_name="get_sales_summary", payload=payload, context=context)
            fallback_text = self.response_builder.build_sales_summary_response(result)
            evidence = [f"tool:get_sales_summary:{result.get('period', '')}"]
            citations = []
        elif intent == "sales_over_period":
            result = self.tool_registry.execute(tool_name="get_sales_over_period", payload=payload, context=context)
            fallback_text = self.response_builder.build_sales_over_period_response(
                result.get("results", []),
                str(result.get("grain") or "day"),
            )
            evidence = [f"tool:get_sales_over_period:{result.get('period', '')}:{result.get('grain', '')}"]
            citations = []
        elif intent == "sales_by_varietal":
            result = self.tool_registry.execute(tool_name="get_sales_by_varietal", payload=payload, context=context)
            fallback_text = self.response_builder.build_sales_by_varietal_response(result.get("results", []))
            evidence = [f"tool:get_sales_by_varietal:{result.get('period', '')}"]
            citations = []
        elif intent == "sales_by_bottle":
            result = self.tool_registry.execute(tool_name="get_sales_by_bottle", payload=payload, context=context)
            fallback_text = self.response_builder.build_sales_by_bottle_response(result.get("results", []))
            evidence = [f"tool:get_sales_by_bottle:{result.get('period', '')}"]
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
            system_prompt=prompt,
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
        run.needs_human = bool(run.metadata.get("pending_approval_ids")) or (not citations and intent == "knowledge_search")
        run.metadata = {**run.metadata, "tool_payload": payload, "used_llm": llm_response.used_llm}
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
        if is_staff:
            order_write_payload = self._detect_order_status_write_payload(message=message, normalized=normalized)
            if order_write_payload is not None:
                return "update_order_status", order_write_payload
            task_payload = self._detect_task_creation_payload(message=message, normalized=normalized)
            if task_payload is not None:
                return "create_support_task", task_payload
        if order_match:
            if "pago" in normalized or "payment" in normalized:
                return "payment_issue", {"order_number": order_match.group(0).upper()}
            return "order_status", {"order_number": order_match.group(0).upper()}
        if is_staff and any(keyword in normalized for keyword in ["ventas", "facturacion", "ingresos"]):
            sales_payload = self._detect_sales_payload(normalized)
            if "varietal" in normalized:
                return "sales_by_varietal", sales_payload
            if any(keyword in normalized for keyword in ["botella", "etiqueta", "sku"]):
                return "sales_by_bottle", sales_payload
            if any(keyword in normalized for keyword in ["por dia", "por semana", "por mes", "periodo"]):
                return "sales_over_period", sales_payload
            return "sales_summary", sales_payload
        if is_staff and "stock" in normalized:
            return "low_stock", {"limit": 5}
        if is_staff and ("pendiente" in normalized or "preparando" in normalized) and "pedido" in normalized:
            return "pending_orders", {"limit": 5}
        if any(keyword in normalized for keyword in ["vino", "malbec", "cabernet", "blend", "etiqueta"]):
            return "catalog_search", {"query": message}
        return "knowledge_search", {}

    def _detect_sales_payload(self, normalized_message: str) -> dict[str, object]:
        """Infer a date window and grouping grain for sales analytics."""
        payload: dict[str, object] = {"period": "last_30_days"}
        if "hoy" in normalized_message:
            today = timezone.localdate().isoformat()
            payload = {"start_date": today, "end_date": today}
        elif "semana" in normalized_message:
            payload["period"] = "last_7_days"
        elif "mes pasado" in normalized_message:
            payload["period"] = "previous_month"
        elif "este mes" in normalized_message or "mes actual" in normalized_message:
            payload["period"] = "current_month"

        if "por semana" in normalized_message:
            payload["grain"] = "week"
        elif "por mes" in normalized_message:
            payload["grain"] = "month"
        else:
            payload["grain"] = "day"
        return payload

    def _detect_order_status_write_payload(
        self,
        *,
        message: str,
        normalized: str,
    ) -> dict[str, object] | None:
        """Detect explicit operator requests to update an order status."""
        order_match = ORDER_NUMBER_RE.search(message)
        if order_match is None:
            return None
        if not any(keyword in normalized for keyword in ["marc", "actualiz", "cambi", "pone", "deja"]):
            return None

        status_map = [
            ("listo para enviar", "ready_to_ship"),
            ("lista para enviar", "ready_to_ship"),
            ("preparando", "preparing"),
            ("enviado", "shipped"),
            ("despachado", "shipped"),
            ("entregado", "delivered"),
            ("cancelado", "cancelled"),
            ("pagado", "paid"),
        ]
        target_status = next((status for phrase, status in status_map if phrase in normalized), None)
        if target_status is None:
            return None

        payload: dict[str, object] = {
            "order_number": order_match.group(0).upper(),
            "new_status": target_status,
            "note": message,
        }
        tracking_match = TRACKING_RE.search(message)
        if tracking_match is not None:
            payload["tracking_number"] = tracking_match.group(1).upper()
        return payload

    def _detect_task_creation_payload(
        self,
        *,
        message: str,
        normalized: str,
    ) -> dict[str, object] | None:
        """Detect guided operator requests to create a support task."""
        task_triggers = [
            "crea una tarea",
            "crea tarea",
            "creame una tarea",
            "abrí una tarea",
            "abri una tarea",
            "segui el pedido",
            "segui este pedido",
        ]
        if not any(trigger in normalized for trigger in task_triggers):
            return None

        order_match = ORDER_NUMBER_RE.search(message)
        email_match = EMAIL_RE.search(message)
        priority = "urgent" if "urgente" in normalized else ("high" if "alta prioridad" in normalized else "medium")
        task_type = "order_issue" if any(keyword in normalized for keyword in ["pedido", "pago", "tracking", "envio"]) else "support_follow_up"
        title = (
            f"Seguimiento manual · {order_match.group(0).upper()}"
            if order_match is not None
            else "Seguimiento manual solicitado desde Copilot"
        )

        payload: dict[str, object] = {
            "title": title,
            "description": message,
            "task_type": task_type,
            "priority": priority,
        }
        if order_match is not None:
            payload["order_number"] = order_match.group(0).upper()
        if email_match is not None:
            payload["customer_email"] = email_match.group(0).lower()
        return payload
