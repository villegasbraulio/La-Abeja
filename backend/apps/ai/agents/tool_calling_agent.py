"""OpenAI-powered tool-calling agent."""

from __future__ import annotations

import json
from dataclasses import dataclass

from django.conf import settings

from apps.ai.tools.base import ToolContext
from apps.ai.tools.registry import ToolRegistry


@dataclass(slots=True)
class ToolCallingAgentResult:
    """Normalized result from a tool-calling run."""

    text: str
    model: str
    used_llm: bool
    citations: list[dict[str, object]]
    metadata: dict[str, object]


class OpenAIToolCallingAgent:
    """Run a multi-step tool loop through OpenAI Responses API."""

    def __init__(self) -> None:
        """Create the OpenAI client lazily."""
        self._client = None

    def run(
        self,
        *,
        message: str,
        mode: str,
        context: ToolContext,
        tool_registry: ToolRegistry,
        prompt: str,
    ) -> ToolCallingAgentResult | None:
        """Attempt a tool-calling conversation and return the final text."""
        if not settings.AI_USE_LLM or not settings.AI_USE_TOOL_CALLING or not settings.OPENAI_API_KEY:
            return None

        try:
            from openai import OpenAI
        except ImportError:
            return None

        if self._client is None:
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)

        tool_names = self._tool_names_for_context(context=context)
        tools = tool_registry.get_tool_definitions(tool_names)
        citations: list[dict[str, object]] = []
        executed_tools: list[str] = []

        try:
            response = self._client.responses.create(
                model=settings.AI_CHAT_MODEL,
                input=[
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Conversation mode: {mode}\n"
                            f"Conversation id: {context.run.conversation_id or 'none'}\n"
                            f"Actor type: {'staff' if context.is_staff else 'customer'}\n"
                            f"User message: {message}\n"
                            "Use tools for live state and use knowledge search for policies or support guidance."
                        ),
                    },
                ],
                tools=tools,
            )

            while True:
                tool_calls = [
                    item
                    for item in getattr(response, "output", [])
                    if getattr(item, "type", "") == "function_call"
                ]
                if not tool_calls:
                    break

                tool_outputs: list[dict[str, object]] = []
                for call in tool_calls:
                    tool_name = str(getattr(call, "name", ""))
                    if not tool_registry.has_tool(tool_name):
                        continue
                    raw_arguments = getattr(call, "arguments", "{}") or "{}"
                    try:
                        payload = json.loads(raw_arguments)
                    except json.JSONDecodeError:
                        payload = {}
                    result = tool_registry.execute(tool_name=tool_name, payload=payload, context=context)
                    executed_tools.append(tool_name)
                    if tool_name == "search_knowledge_base":
                        citations.extend(
                            [
                                {
                                    "chunk_id": item.get("chunk_id"),
                                    "document_id": item.get("document_id"),
                                    "document_title": item.get("document_title"),
                                    "section": item.get("section"),
                                }
                                for item in list(result.get("results", []))[:3]
                            ]
                        )
                    tool_outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": getattr(call, "call_id", ""),
                            "output": json.dumps(result, ensure_ascii=True),
                        }
                    )

                response = self._client.responses.create(
                    model=settings.AI_CHAT_MODEL,
                    previous_response_id=response.id,
                    input=tool_outputs,
                )

            text = (getattr(response, "output_text", "") or "").strip()
            if not text:
                return None
            return ToolCallingAgentResult(
                text=text,
                model=settings.AI_CHAT_MODEL,
                used_llm=True,
                citations=citations,
                metadata={"tool_mode": True, "executed_tools": executed_tools},
            )
        except Exception:
            return None

    def _tool_names_for_context(self, *, context: ToolContext) -> list[str]:
        """Select the tools available to the current actor."""
        names = [
            "search_knowledge_base",
            "search_catalog",
            "get_stock_snapshot",
            "classify_customer_message",
            "draft_whatsapp_reply",
            "recommend_wines_for_customer",
        ]
        if context.user_id is not None or context.is_staff:
            names.extend(
                [
                    "get_order_by_number",
                    "search_orders",
                    "get_customer_orders_summary",
                    "generate_shipping_update",
                    "sync_tracking_status",
                    "check_payment_issue",
                ]
            )
        if context.is_staff:
            names.extend(
                [
                    "search_policies",
                    "search_playbooks",
                    "get_answerable_sources",
                    "get_customer_360",
                    "search_internal_notes",
                    "list_low_stock_items",
                    "list_pending_orders",
                    "create_support_task",
                    "create_ticket_and_assign",
                    "update_support_task",
                    "create_payment_followup",
                    "create_internal_note",
                    "escalate_conversation_to_human",
                    "assign_order_issue",
                    "create_shipping_claim",
                    "mark_order_for_review",
                    "create_restock_task",
                    "create_lead_from_conversation",
                    "update_lead_status",
                    "reserve_stock",
                    "release_stock_reservation",
                    "update_order_status",
                    "send_whatsapp_message",
                    "send_support_email",
                    "request_order_cancellation",
                    "get_sales_summary",
                    "get_sales_over_period",
                    "get_sales_by_varietal",
                    "get_sales_by_bottle",
                    "get_top_skus",
                    "get_repeat_customers_metrics",
                    "get_conversion_funnel",
                    "get_returns_and_incidents_metrics",
                    "get_sales_by_channel",
                    "get_margin_estimate_by_product",
                ]
            )
        return names
