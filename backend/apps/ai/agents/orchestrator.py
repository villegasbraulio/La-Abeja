"""Conversation orchestrator for the AI app."""

from __future__ import annotations

import re
from dataclasses import dataclass
from time import perf_counter
from typing import cast
from uuid import UUID

import structlog
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.ai.agents.prompt_manager import PromptManager
from apps.ai.agents.response_builder import ResponseBuilder
from apps.ai.agents.tool_calling_agent import ToolCallingAgent
from apps.ai.models import AgentRun, Conversation, ConversationTurn
from apps.ai.services.llm_client import LLMClient
from apps.ai.tools.base import ToolContext
from apps.ai.tools.registry import ToolRegistry

logger = structlog.get_logger(__name__)

ORDER_NUMBER_RE = re.compile(r"LAB-\d{4}-\d{3,}", re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.IGNORECASE)
TRACKING_RE = re.compile(r"tracking(?:\s+numero)?[:\s]+([A-Z0-9-]+)", re.IGNORECASE)
SKU_RE = re.compile(r"(?:sku|etiqueta)[:\s]+([A-Z0-9-]{4,})", re.IGNORECASE)
QUANTITY_RE = re.compile(r"(\d+)\s+(?:unidad(?:es)?|botella(?:s)?)", re.IGNORECASE)


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
        user_id: UUID | None,
        is_staff: bool,
    ) -> OrchestratorResult:
        """Persist the user message, run the orchestration, and store the assistant reply."""
        started_at = perf_counter()
        if settings.AI_LOG_CONSOLE_DETAILS:
            logger.info(
                "AI_RUN_STARTED",
                conversation_id=str(conversation.id),
                mode=conversation.mode,
                actor_type="staff" if is_staff else "customer",
                message_chars=len(message),
            )
        user_turn = ConversationTurn.objects.create(
            conversation=conversation,
            role=ConversationTurn.Role.USER,
            content=message,
        )
        del user_turn
        agent_type = (
            AgentRun.AgentType.OPS
            if conversation.mode == Conversation.Mode.OPS
            else AgentRun.AgentType.SUPPORT
        )
        run = AgentRun.objects.create(
            conversation=conversation,
            agent_type=agent_type,
            intent="",
            message_text=message,
        )
        context = ToolContext(run=run, user_id=user_id, is_staff=is_staff)
        intent, payload = self._detect_intent(message=message, is_staff=is_staff)
        if settings.AI_LOG_CONSOLE_DETAILS:
            logger.info(
                "AI_INTENT_DETECTED",
                run_id=str(run.id),
                intent=intent,
                payload_keys=sorted(payload.keys()),
            )
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
        agent_attempt_observation = run.metadata.get("provider_observability", {})
        if not isinstance(agent_attempt_observation, dict):
            agent_attempt_observation = {}
        if tool_calling_result is None and not agent_attempt_observation:
            agent_attempt_observation = {
                "fallback_reason": "tool_calling_disabled_or_unavailable"
            }
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
                "execution_path": "agent",
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
            self._log_run_completion(
                run=run,
                execution_path="agent",
                started_at=started_at,
            )
            return OrchestratorResult(assistant_turn=assistant_turn, run=run)

        citations: list[dict[str, object]] = []
        if intent == "search_orders":
            result = self.tool_registry.execute(
                tool_name="search_orders", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_search_orders_response(
                result.get("results", [])
            )
            evidence = ["tool:search_orders"]
            citations = []
        elif intent == "customer_360":
            result = self.tool_registry.execute(
                tool_name="get_customer_360", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_customer_360_response(result)
            evidence = [f"tool:get_customer_360:{result.get('customer', {}).get('email', '')}"]
            citations = []
        elif intent == "customer_orders_summary":
            result = self.tool_registry.execute(
                tool_name="get_customer_orders_summary", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_customer_orders_summary_response(result)
            evidence = [f"tool:get_customer_orders_summary:{result.get('customer_email', '')}"]
            citations = []
        elif intent == "create_support_task":
            result = self.tool_registry.execute(
                tool_name="create_support_task", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_support_task_response(result)
            evidence = [f"tool:create_support_task:{result.get('task_id', '')}"]
            citations = []
        elif intent == "create_payment_followup":
            result = self.tool_registry.execute(
                tool_name="create_payment_followup", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_payment_followup_response(result)
            evidence = [f"tool:create_payment_followup:{result.get('task_id', '')}"]
            citations = []
        elif intent == "create_shipping_claim":
            result = self.tool_registry.execute(
                tool_name="create_shipping_claim", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_shipping_claim_response(result)
            evidence = [f"tool:create_shipping_claim:{result.get('task_id', '')}"]
            citations = []
        elif intent == "reserve_stock":
            result = self.tool_registry.execute(
                tool_name="reserve_stock", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_stock_reservation_response(result)
            evidence = [f"tool:reserve_stock:{result.get('reservation_id', '')}"]
            citations = []
        elif intent == "request_order_cancellation":
            result = self.tool_registry.execute(
                tool_name="request_order_cancellation", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_order_cancellation_response(result)
            evidence = [f"tool:request_order_cancellation:{result.get('order_number', '')}"]
            citations = []
        elif intent == "update_order_status":
            result = self.tool_registry.execute(
                tool_name="update_order_status", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_order_status_update_response(result)
            evidence = [f"tool:update_order_status:{result.get('order_number', '')}"]
            citations = []
        elif intent == "order_status":
            result = self.tool_registry.execute(
                tool_name="get_order_by_number", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_order_status_response(result)
            evidence = [f"tool:get_order_by_number:{result.get('order_number', '')}"]
            citations = []
        elif intent == "low_stock":
            result = self.tool_registry.execute(
                tool_name="list_low_stock_items", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_low_stock_response(
                result.get("results", [])
            )
            evidence = ["tool:list_low_stock_items"]
            citations = []
        elif intent == "pending_orders":
            result = self.tool_registry.execute(
                tool_name="list_pending_orders", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_pending_orders_response(
                result.get("results", [])
            )
            evidence = ["tool:list_pending_orders"]
            citations = []
        elif intent == "payment_issue":
            result = self.tool_registry.execute(
                tool_name="check_payment_issue", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_payment_issue_response(result)
            evidence = [f"tool:check_payment_issue:{result.get('order_number', '')}"]
            citations = []
        elif intent == "shipping_update":
            result = self.tool_registry.execute(
                tool_name="generate_shipping_update", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_shipping_update_response(result)
            evidence = [f"tool:generate_shipping_update:{result.get('order_number', '')}"]
            citations = []
        elif intent == "sales_summary":
            result = self.tool_registry.execute(
                tool_name="get_sales_summary", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_sales_summary_response(result)
            evidence = [f"tool:get_sales_summary:{result.get('period', '')}"]
            citations = []
        elif intent == "sales_over_period":
            result = self.tool_registry.execute(
                tool_name="get_sales_over_period", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_sales_over_period_response(
                result.get("results", []),
                str(result.get("grain") or "day"),
            )
            evidence = [
                f"tool:get_sales_over_period:{result.get('period', '')}:{result.get('grain', '')}"
            ]
            citations = []
        elif intent == "sales_by_varietal":
            result = self.tool_registry.execute(
                tool_name="get_sales_by_varietal", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_sales_by_varietal_response(
                result.get("results", [])
            )
            evidence = [f"tool:get_sales_by_varietal:{result.get('period', '')}"]
            citations = []
        elif intent == "sales_by_bottle":
            result = self.tool_registry.execute(
                tool_name="get_sales_by_bottle", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_sales_by_bottle_response(
                result.get("results", [])
            )
            evidence = [f"tool:get_sales_by_bottle:{result.get('period', '')}"]
            citations = []
        elif intent == "catalog_search":
            result = self.tool_registry.execute(
                tool_name="search_catalog", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_catalog_response(result.get("results", []))
            evidence = ["tool:search_catalog"]
            citations = []
        elif intent == "visit_search":
            result = self.tool_registry.execute(
                tool_name="search_visit_context", payload=payload, context=context
            )
            fallback_text = self.response_builder.build_visit_context_response(result)
            evidence = ["tool:search_visit_context"]
            citations = []
        else:
            result = self.tool_registry.execute(
                tool_name="search_knowledge_base",
                payload={"query": message},
                context=context,
            )
            kb_results = cast(list[dict[str, object]], result.get("results", []))
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
            metadata={
                "intent": intent,
                "used_llm": llm_response.used_llm,
                "model": llm_response.model,
                **llm_response.metadata,
            },
        )

        run.model = llm_response.model
        run.status = AgentRun.Status.COMPLETED
        run.response_text = assistant_turn.content
        run.citations = citations
        run.confidence = 0.950 if intent != "knowledge_search" else (0.880 if citations else 0.350)
        run.needs_human = bool(run.metadata.get("pending_approval_ids")) or (
            not citations and intent == "knowledge_search"
        )
        run.metadata = {
            **run.metadata,
            "tool_payload": payload,
            "used_llm": llm_response.used_llm,
            "execution_path": (
                "grounded_llm" if llm_response.used_llm else "deterministic_fallback"
            ),
            "agent_attempt_observability": agent_attempt_observation,
            **llm_response.metadata,
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
        self._log_run_completion(
            run=run,
            execution_path=(
                "grounded_llm" if llm_response.used_llm else "deterministic_fallback"
            ),
            started_at=started_at,
        )
        return OrchestratorResult(assistant_turn=assistant_turn, run=run)

    def _log_run_completion(
        self,
        *,
        run: AgentRun,
        execution_path: str,
        started_at: float,
    ) -> None:
        """Emit one safe console summary that makes agent versus fallback obvious."""
        if not settings.AI_LOG_CONSOLE_DETAILS:
            return
        provider_observation = run.metadata.get("provider_observability", {})
        observation = (
            provider_observation if isinstance(provider_observation, dict) else {}
        )
        agent_attempt = run.metadata.get("agent_attempt_observability", {})
        if not isinstance(agent_attempt, dict):
            agent_attempt = {}
        tool_executions = list(
            run.tool_executions.values_list("tool_name", "status")
        )
        is_agent = execution_path == "agent"
        logger.info(
            "AI_AGENT_COMPLETED" if is_agent else "AI_FALLBACK_COMPLETED",
            run_id=str(run.id),
            conversation_id=str(run.conversation_id),
            execution_path=execution_path,
            agent_active=is_agent,
            fallback_used=not is_agent,
            intent=run.intent,
            model=run.model,
            total_latency_ms=int((perf_counter() - started_at) * 1000),
            provider_latency_ms=observation.get("latency_ms"),
            retry_count=observation.get("retry_count", 0),
            agent_fallback_reason=agent_attempt.get("fallback_reason"),
            fallback_reason=(
                observation.get("fallback_reason")
                or (
                    "llm_disabled_or_unavailable"
                    if execution_path == "deterministic_fallback"
                    else None
                )
            ),
            token_usage=observation.get("token_usage", {}),
            estimated_cost_usd=observation.get("estimated_cost_usd"),
            tools=[{"name": name, "status": status} for name, status in tool_executions],
            citation_count=len(run.citations),
            needs_human=run.needs_human,
        )

    def _detect_intent(self, *, message: str, is_staff: bool) -> tuple[str, dict[str, object]]:
        """Infer a narrow intent from the message using business heuristics."""
        normalized = message.lower()
        order_match = ORDER_NUMBER_RE.search(message)
        if is_staff:
            order_search_payload = self._detect_order_search_payload(
                message=message, normalized=normalized
            )
            if order_search_payload is not None:
                return "search_orders", order_search_payload
            customer_360_payload = self._detect_customer_context_payload(
                message=message, normalized=normalized
            )
            if customer_360_payload is not None:
                intent = (
                    "customer_360"
                    if "360" in normalized or "perfil" in normalized
                    else "customer_orders_summary"
                )
                return intent, customer_360_payload
            reserve_stock_payload = self._detect_reserve_stock_payload(
                message=message, normalized=normalized
            )
            if reserve_stock_payload is not None:
                return "reserve_stock", reserve_stock_payload
            cancellation_payload = self._detect_order_cancellation_payload(
                message=message, normalized=normalized
            )
            if cancellation_payload is not None:
                return "request_order_cancellation", cancellation_payload
            order_write_payload = self._detect_order_status_write_payload(
                message=message, normalized=normalized
            )
            if order_write_payload is not None:
                return "update_order_status", order_write_payload
            payment_followup_payload = self._detect_payment_followup_payload(
                message=message, normalized=normalized
            )
            if payment_followup_payload is not None:
                return "create_payment_followup", payment_followup_payload
            shipping_claim_payload = self._detect_shipping_claim_payload(
                message=message, normalized=normalized
            )
            if shipping_claim_payload is not None:
                return "create_shipping_claim", shipping_claim_payload
            task_payload = self._detect_task_creation_payload(
                message=message, normalized=normalized
            )
            if task_payload is not None:
                return "create_support_task", task_payload
        if order_match:
            if any(
                keyword in normalized for keyword in ["tracking", "envio", "despacho", "en camino"]
            ):
                return "shipping_update", {"order_number": order_match.group(0).upper()}
            if "pago" in normalized or "payment" in normalized:
                return "payment_issue", {"order_number": order_match.group(0).upper()}
            return "order_status", {"order_number": order_match.group(0).upper()}
        if is_staff and any(
            keyword in normalized for keyword in ["ventas", "facturacion", "ingresos"]
        ):
            sales_payload = self._detect_sales_payload(normalized)
            if "varietal" in normalized:
                return "sales_by_varietal", sales_payload
            if any(keyword in normalized for keyword in ["botella", "etiqueta", "sku"]):
                return "sales_by_bottle", sales_payload
            if any(
                keyword in normalized for keyword in ["por dia", "por semana", "por mes", "periodo"]
            ):
                return "sales_over_period", sales_payload
            return "sales_summary", sales_payload
        if is_staff and "stock" in normalized:
            return "low_stock", {"limit": 5}
        if (
            is_staff
            and ("pendiente" in normalized or "preparando" in normalized)
            and "pedido" in normalized
        ):
            return "pending_orders", {"limit": 5}
        if is_staff and any(
            keyword in normalized
            for keyword in [
                "visita",
                "visitas",
                "evento",
                "eventos",
                "maridaj",
                "degust",
                "turno",
                "cupo",
                "hospitalidad",
            ]
        ):
            return "visit_search", {"query": message, "limit": 5}
        if any(
            keyword in normalized for keyword in ["vino", "malbec", "cabernet", "blend", "etiqueta"]
        ):
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
        if not any(
            keyword in normalized for keyword in ["marc", "actualiz", "cambi", "pone", "deja"]
        ):
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
        target_status = next(
            (status for phrase, status in status_map if phrase in normalized), None
        )
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
        priority = (
            "urgent"
            if "urgente" in normalized
            else ("high" if "alta prioridad" in normalized else "medium")
        )
        task_type = (
            "order_issue"
            if any(keyword in normalized for keyword in ["pedido", "pago", "tracking", "envio"])
            else "support_follow_up"
        )
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

    def _detect_order_search_payload(
        self,
        *,
        message: str,
        normalized: str,
    ) -> dict[str, object] | None:
        """Detect guided order-search prompts for staff operators."""
        search_triggers = [
            "busca pedidos",
            "buscá pedidos",
            "mostrame pedidos",
            "mostrar pedidos",
            "pedidos con",
            "pedidos de",
            "pedidos del cliente",
        ]
        if not any(trigger in normalized for trigger in search_triggers):
            return None

        payload: dict[str, object] = {"limit": 10}
        email_match = EMAIL_RE.search(message)
        if email_match is not None:
            payload["customer_email"] = email_match.group(0).lower()

        if "rechaz" in normalized or "fallid" in normalized:
            payload["statuses"] = ["payment_failed"]
        elif "cancel" in normalized:
            payload["statuses"] = ["cancelled"]
        elif "enviado" in normalized or "despachado" in normalized:
            payload["statuses"] = ["shipped"]
        elif "entregado" in normalized:
            payload["statuses"] = ["delivered"]
        elif "pagado" in normalized:
            payload["statuses"] = ["paid"]

        if "semana" in normalized:
            payload["period"] = "last_7_days"
        elif "mes pasado" in normalized:
            payload["period"] = "previous_month"
        elif "este mes" in normalized:
            payload["period"] = "current_month"
        elif "hoy" in normalized:
            today = timezone.localdate().isoformat()
            payload["start_date"] = today
            payload["end_date"] = today

        return payload

    def _detect_customer_context_payload(
        self,
        *,
        message: str,
        normalized: str,
    ) -> dict[str, object] | None:
        """Detect customer-summary or 360 prompts."""
        customer_triggers = [
            "360 del cliente",
            "customer 360",
            "perfil del cliente",
            "resumen del cliente",
            "historial del cliente",
        ]
        if not any(trigger in normalized for trigger in customer_triggers):
            return None

        email_match = EMAIL_RE.search(message)
        order_match = ORDER_NUMBER_RE.search(message)
        payload: dict[str, object] = {}
        if email_match is not None:
            payload["customer_email"] = email_match.group(0).lower()
        if order_match is not None:
            payload["order_number"] = order_match.group(0).upper()
        return payload if payload else None

    def _detect_payment_followup_payload(
        self,
        *,
        message: str,
        normalized: str,
    ) -> dict[str, object] | None:
        """Detect prompts that ask to create a payment follow-up task."""
        if not any(
            trigger in normalized
            for trigger in [
                "seguimiento de pago",
                "followup de pago",
                "revisa el pago",
                "segui el pago",
            ]
        ):
            return None
        order_match = ORDER_NUMBER_RE.search(message)
        if order_match is None:
            return None
        payload: dict[str, object] = {"order_number": order_match.group(0).upper()}
        email_match = EMAIL_RE.search(message)
        if email_match is not None:
            payload["customer_email"] = email_match.group(0).lower()
        return payload

    def _detect_shipping_claim_payload(
        self,
        *,
        message: str,
        normalized: str,
    ) -> dict[str, object] | None:
        """Detect prompts to create shipping or logistics claims."""
        if not any(
            trigger in normalized
            for trigger in [
                "reclamo logist",
                "reclamo de envio",
                "shipping claim",
                "demora de envio",
            ]
        ):
            return None
        order_match = ORDER_NUMBER_RE.search(message)
        if order_match is None:
            return None
        claim_reason = "demora_envio"
        if "tracking" in normalized:
            claim_reason = "tracking_missing"
        elif "extravi" in normalized:
            claim_reason = "shipment_lost"
        return {
            "order_number": order_match.group(0).upper(),
            "claim_reason": claim_reason,
            "summary": message,
        }

    def _detect_order_cancellation_payload(
        self,
        *,
        message: str,
        normalized: str,
    ) -> dict[str, object] | None:
        """Detect explicit requests to cancel an order."""
        order_match = ORDER_NUMBER_RE.search(message)
        if order_match is None:
            return None
        if not any(
            trigger in normalized
            for trigger in [
                "pedi cancel",
                "pedí cancel",
                "cancela el pedido",
                "cancelá el pedido",
                "anula el pedido",
                "anulá el pedido",
            ]
        ):
            return None
        return {
            "order_number": order_match.group(0).upper(),
            "reason": message,
        }

    def _detect_reserve_stock_payload(
        self,
        *,
        message: str,
        normalized: str,
    ) -> dict[str, object] | None:
        """Detect explicit stock-reservation prompts."""
        if not any(trigger in normalized for trigger in ["reserv", "separ", "bloquea stock"]):
            return None
        sku_match = SKU_RE.search(message)
        quantity_match = QUANTITY_RE.search(message)
        if sku_match is None or quantity_match is None:
            return None

        payload: dict[str, object] = {
            "sku": sku_match.group(1).upper(),
            "quantity": int(quantity_match.group(1)),
            "reason": message,
        }
        order_match = ORDER_NUMBER_RE.search(message)
        if order_match is not None:
            payload["order_number"] = order_match.group(0).upper()
        email_match = EMAIL_RE.search(message)
        if email_match is not None:
            payload["customer_email"] = email_match.group(0).lower()
        return payload
