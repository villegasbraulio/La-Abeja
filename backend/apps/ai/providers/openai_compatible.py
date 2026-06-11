"""OpenAI-compatible provider adapters for chat and tool-calling."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from apps.ai.providers.base import LLMProvider, ProviderTextResponse, ProviderToolCallResult
from apps.ai.tools.base import ToolContext
from apps.ai.tools.registry import ToolRegistry


@dataclass(slots=True)
class OpenAICompatibleProviderConfig:
    """Static configuration for an OpenAI-compatible provider."""

    provider_name: str
    api_key: str
    model: str
    base_url: str | None = None


class OpenAICompatibleProvider(LLMProvider):
    """Adapter over the OpenAI Python SDK for OpenAI-compatible APIs."""

    def __init__(self, config: OpenAICompatibleProviderConfig) -> None:
        """Store provider configuration and lazily create the SDK client."""
        self._config = config
        self._client = None
        self.provider_name = config.provider_name

    def is_available(self) -> bool:
        """Return True when the provider has a configured API key."""
        return bool(self._config.api_key)

    def generate_grounded_response(
        self,
        *,
        system_prompt: str,
        user_message: str,
        evidence: list[str],
    ) -> ProviderTextResponse | None:
        """Use the responses API to generate a grounded answer."""
        client = self._get_client()
        if client is None:
            return None

        try:
            response = client.responses.create(
                model=self._config.model,
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
        except Exception:
            return None

        output_text = getattr(response, "output_text", "").strip()
        if not output_text:
            return None
        return ProviderTextResponse(text=output_text, model=self._config.model)

    def run_tool_calling(
        self,
        *,
        message: str,
        mode: str,
        context: ToolContext,
        tool_registry: ToolRegistry,
        prompt: str,
    ) -> ProviderToolCallResult | None:
        """Run the local tool-calling loop via the responses API."""
        client = self._get_client()
        if client is None:
            return None

        if self.provider_name == "groq":
            return self._run_tool_calling_with_chat_completions(
                client=client,
                message=message,
                mode=mode,
                context=context,
                tool_registry=tool_registry,
                prompt=prompt,
            )

        return self._run_tool_calling_with_responses(
            client=client,
            message=message,
            mode=mode,
            context=context,
            tool_registry=tool_registry,
            prompt=prompt,
        )

    def _run_tool_calling_with_responses(
        self,
        *,
        client: Any,
        message: str,
        mode: str,
        context: ToolContext,
        tool_registry: ToolRegistry,
        prompt: str,
    ) -> ProviderToolCallResult | None:
        """Run tool calling through the Responses API."""
        tool_names = self._tool_names_for_context(context=context)
        tools = tool_registry.get_tool_definitions(tool_names)
        citations: list[dict[str, object]] = []
        executed_tools: list[str] = []

        try:
            response = client.responses.create(
                model=self._config.model,
                input=[
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": self._build_tool_loop_user_message(
                            message=message,
                            mode=mode,
                            context=context,
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
                    result = tool_registry.execute(
                        tool_name=tool_name,
                        payload=payload,
                        context=context,
                    )
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

                response = client.responses.create(
                    model=self._config.model,
                    previous_response_id=response.id,
                    input=tool_outputs,
                )
        except Exception:
            return None

        text = (getattr(response, "output_text", "") or "").strip()
        if not text:
            return None
        return ProviderToolCallResult(
            text=text,
            model=self._config.model,
            citations=citations,
            metadata={"tool_mode": True, "executed_tools": executed_tools},
        )

    def _run_tool_calling_with_chat_completions(
        self,
        *,
        client: Any,
        message: str,
        mode: str,
        context: ToolContext,
        tool_registry: ToolRegistry,
        prompt: str,
    ) -> ProviderToolCallResult | None:
        """Run tool calling through Chat Completions for providers without response chaining."""
        tool_names = self._tool_names_for_context(context=context)
        tools = self._as_chat_completion_tools(tool_registry.get_tool_definitions(tool_names))
        citations: list[dict[str, object]] = []
        executed_tools: list[str] = []
        messages: list[dict[str, object]] = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": self._build_tool_loop_user_message(
                    message=message,
                    mode=mode,
                    context=context,
                ),
            },
        ]

        try:
            for _ in range(8):
                response = client.chat.completions.create(
                    model=self._config.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
                choices = list(getattr(response, "choices", []) or [])
                if not choices:
                    return None

                response_message = getattr(choices[0], "message", None)
                if response_message is None:
                    return None
                messages.append(self._chat_completion_message_to_dict(response_message))

                tool_calls = list(getattr(response_message, "tool_calls", []) or [])
                if not tool_calls:
                    text = self._extract_message_text(response_message)
                    if not text:
                        return None
                    return ProviderToolCallResult(
                        text=text,
                        model=self._config.model,
                        citations=citations,
                        metadata={"tool_mode": True, "executed_tools": executed_tools},
                    )

                for call in tool_calls:
                    function = getattr(call, "function", None)
                    tool_name = str(getattr(function, "name", ""))
                    raw_arguments = getattr(function, "arguments", "{}") or "{}"
                    tool_call_id = str(getattr(call, "id", ""))

                    if not tool_registry.has_tool(tool_name):
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "name": tool_name or "unknown_tool",
                                "content": json.dumps(
                                    {"error": "unknown_tool"},
                                    ensure_ascii=True,
                                ),
                            }
                        )
                        continue

                    try:
                        payload = json.loads(raw_arguments)
                    except json.JSONDecodeError:
                        payload = {}
                    result = tool_registry.execute(
                        tool_name=tool_name,
                        payload=payload,
                        context=context,
                    )
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
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": json.dumps(result, ensure_ascii=True),
                        }
                    )
        except Exception:
            return None

        return None

    def _get_client(self):
        """Instantiate the OpenAI SDK client lazily."""
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
        except ImportError:
            return None

        client_kwargs = {"api_key": self._config.api_key}
        if self._config.base_url:
            client_kwargs["base_url"] = self._config.base_url
        self._client = OpenAI(**client_kwargs)
        return self._client

    def _build_tool_loop_user_message(
        self,
        *,
        message: str,
        mode: str,
        context: ToolContext,
    ) -> str:
        """Build the normalized tool-loop prompt payload."""
        return (
            f"Conversation mode: {mode}\n"
            f"Conversation id: {context.run.conversation_id or 'none'}\n"
            f"Actor type: {'staff' if context.is_staff else 'customer'}\n"
            f"User message: {message}\n"
            "Use tools for live state and use knowledge search "
            "for policies or support guidance."
        )

    def _as_chat_completion_tools(
        self,
        tool_definitions: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        """Adapt Responses-style tool definitions into Chat Completions format."""
        converted: list[dict[str, object]] = []
        for definition in tool_definitions:
            converted.append(
                {
                    "type": "function",
                    "function": {
                        "name": definition["name"],
                        "description": definition["description"],
                        "parameters": definition["parameters"],
                    },
                }
            )
        return converted

    def _chat_completion_message_to_dict(self, message: Any) -> dict[str, object]:
        """Normalize a chat completion message for the next iteration."""
        payload: dict[str, object] = {"role": "assistant"}
        content = self._extract_message_text(message)
        if content is not None:
            payload["content"] = content

        tool_calls = list(getattr(message, "tool_calls", []) or [])
        if tool_calls:
            payload["tool_calls"] = [
                {
                    "id": str(getattr(call, "id", "")),
                    "type": "function",
                    "function": {
                        "name": str(getattr(getattr(call, "function", None), "name", "")),
                        "arguments": str(
                            getattr(getattr(call, "function", None), "arguments", "{}") or "{}"
                        ),
                    },
                }
                for call in tool_calls
            ]
        if "content" not in payload and not tool_calls:
            payload["content"] = ""
        return payload

    def _extract_message_text(self, message: Any) -> str | None:
        """Read textual content from either an SDK message object or raw content."""
        content = getattr(message, "content", message)
        if isinstance(content, str):
            stripped = content.strip()
            return stripped or None
        if content is None:
            return None
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text" and isinstance(item.get("text"), str):
                        parts.append(item["text"])
                        continue
                    text_payload = item.get("text")
                    if isinstance(text_payload, dict) and isinstance(
                        text_payload.get("value"), str
                    ):
                        parts.append(text_payload["value"])
                        continue
                text_attr = getattr(item, "text", None)
                if isinstance(text_attr, str):
                    parts.append(text_attr)
                    continue
                text_value = getattr(text_attr, "value", None)
                if isinstance(text_value, str):
                    parts.append(text_value)
            joined = "\n".join(part.strip() for part in parts if part and part.strip())
            return joined or None
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
