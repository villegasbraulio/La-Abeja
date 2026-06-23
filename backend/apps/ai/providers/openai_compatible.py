"""OpenAI-compatible provider adapters for chat and tool-calling."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, cast

import structlog
from django.conf import settings

from apps.ai.providers.base import LLMProvider, ProviderTextResponse, ProviderToolCallResult
from apps.ai.tools.base import ToolContext
from apps.ai.tools.registry import ToolRegistry

logger = structlog.get_logger(__name__)


class _ProviderCallError(Exception):
    """Wrap a terminal provider error together with retries already attempted."""

    def __init__(self, cause: Exception, retry_count: int) -> None:
        super().__init__(str(cause))
        self.cause = cause
        self.retry_count = retry_count


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
        self.last_observation: dict[str, object] = {}

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
            self._record_observation(
                operation="grounded_response",
                started_at=time.perf_counter(),
                fallback_reason="client_unavailable",
            )
            return None

        started_at = time.perf_counter()
        try:
            response, retry_count = self._call_with_retries(
                client.responses.create,
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
        except Exception as exc:
            self._record_observation(
                operation="grounded_response",
                started_at=started_at,
                fallback_reason="provider_exception",
                error=exc,
            )
            return None

        output_text = getattr(response, "output_text", "").strip()
        if not output_text:
            self._record_observation(
                operation="grounded_response",
                started_at=started_at,
                fallback_reason="empty_output",
                retry_count=retry_count,
                usage=self._extract_usage(response),
            )
            return None
        observation = self._record_observation(
            operation="grounded_response",
            started_at=started_at,
            retry_count=retry_count,
            usage=self._extract_usage(response),
        )
        return ProviderTextResponse(
            text=output_text,
            model=self._config.model,
            metadata=observation,
        )

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
            observation = self._record_observation(
                operation="tool_calling",
                started_at=time.perf_counter(),
                fallback_reason="client_unavailable",
            )
            self._attach_observation(context=context, observation=observation)
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
        usage = self._empty_usage()
        retry_count = 0
        started_at = time.perf_counter()

        try:
            response, retries = self._call_with_retries(
                client.responses.create,
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
            retry_count += retries
            self._merge_usage(usage, self._extract_usage(response))

            for _ in range(self._max_tool_iterations()):
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
                        result_items = cast(list[dict[str, object]], result.get("results", []))
                        citations.extend(
                            [
                                {
                                    "chunk_id": item.get("chunk_id"),
                                    "document_id": item.get("document_id"),
                                    "document_title": item.get("document_title"),
                                    "section": item.get("section"),
                                }
                                for item in result_items[:3]
                            ]
                        )
                    tool_outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": getattr(call, "call_id", ""),
                            "output": json.dumps(result, ensure_ascii=True),
                        }
                    )

                response, retries = self._call_with_retries(
                    client.responses.create,
                    model=self._config.model,
                    previous_response_id=response.id,
                    input=tool_outputs,
                )
                retry_count += retries
                self._merge_usage(usage, self._extract_usage(response))
            else:
                observation = self._record_observation(
                    operation="tool_calling",
                    started_at=started_at,
                    fallback_reason="max_tool_iterations",
                    retry_count=retry_count,
                    usage=usage,
                    extra={"executed_tools": executed_tools},
                )
                self._attach_observation(context=context, observation=observation)
                return None
        except Exception as exc:
            observation = self._record_observation(
                operation="tool_calling",
                started_at=started_at,
                fallback_reason="provider_exception",
                retry_count=retry_count,
                usage=usage,
                error=exc,
                extra={"executed_tools": executed_tools},
            )
            self._attach_observation(context=context, observation=observation)
            return None

        text = (getattr(response, "output_text", "") or "").strip()
        if not text:
            observation = self._record_observation(
                operation="tool_calling",
                started_at=started_at,
                fallback_reason="empty_output",
                retry_count=retry_count,
                usage=usage,
                extra={"executed_tools": executed_tools},
            )
            self._attach_observation(context=context, observation=observation)
            return None
        observation = self._record_observation(
            operation="tool_calling",
            started_at=started_at,
            retry_count=retry_count,
            usage=usage,
            extra={"executed_tools": executed_tools},
        )
        self._attach_observation(context=context, observation=observation)
        return ProviderToolCallResult(
            text=text,
            model=self._config.model,
            citations=citations,
            metadata={"tool_mode": True, "executed_tools": executed_tools, **observation},
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
        usage = self._empty_usage()
        retry_count = 0
        started_at = time.perf_counter()
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
            for _ in range(self._max_tool_iterations()):
                response, retries = self._call_with_retries(
                    client.chat.completions.create,
                    model=self._config.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
                retry_count += retries
                self._merge_usage(usage, self._extract_usage(response))
                choices = list(getattr(response, "choices", []) or [])
                if not choices:
                    observation = self._record_observation(
                        operation="tool_calling",
                        started_at=started_at,
                        fallback_reason="missing_choices",
                        retry_count=retry_count,
                        usage=usage,
                        extra={"executed_tools": executed_tools},
                    )
                    self._attach_observation(context=context, observation=observation)
                    return None

                response_message = getattr(choices[0], "message", None)
                if response_message is None:
                    observation = self._record_observation(
                        operation="tool_calling",
                        started_at=started_at,
                        fallback_reason="missing_message",
                        retry_count=retry_count,
                        usage=usage,
                        extra={"executed_tools": executed_tools},
                    )
                    self._attach_observation(context=context, observation=observation)
                    return None
                messages.append(self._chat_completion_message_to_dict(response_message))

                tool_calls = list(getattr(response_message, "tool_calls", []) or [])
                if not tool_calls:
                    text = self._extract_message_text(response_message)
                    if not text:
                        observation = self._record_observation(
                            operation="tool_calling",
                            started_at=started_at,
                            fallback_reason="empty_output",
                            retry_count=retry_count,
                            usage=usage,
                            extra={"executed_tools": executed_tools},
                        )
                        self._attach_observation(context=context, observation=observation)
                        return None
                    observation = self._record_observation(
                        operation="tool_calling",
                        started_at=started_at,
                        retry_count=retry_count,
                        usage=usage,
                        extra={"executed_tools": executed_tools},
                    )
                    self._attach_observation(context=context, observation=observation)
                    return ProviderToolCallResult(
                        text=text,
                        model=self._config.model,
                        citations=citations,
                        metadata={
                            "tool_mode": True,
                            "executed_tools": executed_tools,
                            **observation,
                        },
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
                        result_items = cast(list[dict[str, object]], result.get("results", []))
                        citations.extend(
                            [
                                {
                                    "chunk_id": item.get("chunk_id"),
                                    "document_id": item.get("document_id"),
                                    "document_title": item.get("document_title"),
                                    "section": item.get("section"),
                                }
                                for item in result_items[:3]
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
        except Exception as exc:
            observation = self._record_observation(
                operation="tool_calling",
                started_at=started_at,
                fallback_reason="provider_exception",
                retry_count=retry_count,
                usage=usage,
                error=exc,
                extra={"executed_tools": executed_tools},
            )
            self._attach_observation(context=context, observation=observation)
            return None

        observation = self._record_observation(
            operation="tool_calling",
            started_at=started_at,
            fallback_reason="max_tool_iterations",
            retry_count=retry_count,
            usage=usage,
            extra={"executed_tools": executed_tools},
        )
        self._attach_observation(context=context, observation=observation)
        return None

    def _call_with_retries(self, callable_obj: Any, **kwargs: object) -> tuple[Any, int]:
        """Call a provider endpoint and retry transient failures with bounded backoff."""
        max_retries = max(int(getattr(settings, "AI_PROVIDER_MAX_RETRIES", 2)), 0)
        base_seconds = max(
            float(getattr(settings, "AI_PROVIDER_RETRY_BASE_SECONDS", 0.25)), 0.0
        )
        retry_count = 0
        while True:
            try:
                return callable_obj(**kwargs), retry_count
            except Exception as exc:
                if retry_count >= max_retries or not self._is_retryable_error(exc):
                    raise _ProviderCallError(exc, retry_count) from exc
                retry_count += 1
                logger.warning(
                    "ai_provider_retry",
                    provider=self.provider_name,
                    model=self._config.model,
                    retry_count=retry_count,
                    error_type=type(exc).__name__,
                )
                if base_seconds:
                    time.sleep(base_seconds * (2 ** (retry_count - 1)))

    def _is_retryable_error(self, exc: Exception) -> bool:
        """Return whether an SDK/network error is safe to retry."""
        status_code = getattr(exc, "status_code", None)
        if status_code in {408, 409, 429} or (
            isinstance(status_code, int) and status_code >= 500
        ):
            return True
        error_name = type(exc).__name__.lower()
        return any(
            marker in error_name
            for marker in ("timeout", "connection", "ratelimit", "internalserver")
        )

    def _max_tool_iterations(self) -> int:
        """Return the configured hard limit for model/tool round trips."""
        return max(int(getattr(settings, "AI_PROVIDER_MAX_TOOL_ITERATIONS", 8)), 1)

    def _empty_usage(self) -> dict[str, int]:
        """Return an empty normalized token usage accumulator."""
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    def _extract_usage(self, response: Any) -> dict[str, int]:
        """Normalize token usage from Responses or Chat Completions envelopes."""
        usage = getattr(response, "usage", None)
        input_tokens = self._usage_value(usage, "input_tokens", "prompt_tokens")
        output_tokens = self._usage_value(usage, "output_tokens", "completion_tokens")
        total_tokens = self._usage_value(usage, "total_tokens")
        if not total_tokens:
            total_tokens = input_tokens + output_tokens
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

    def _usage_value(self, usage: Any, *names: str) -> int:
        """Read one integer usage field from an object or mapping."""
        for name in names:
            value = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
            if isinstance(value, int):
                return value
        return 0

    def _merge_usage(self, accumulator: dict[str, int], usage: dict[str, int]) -> None:
        """Add one provider response's token counts to the request accumulator."""
        for key in accumulator:
            accumulator[key] += usage.get(key, 0)

    def _estimated_cost_usd(self, usage: dict[str, int]) -> float | None:
        """Estimate cost when deployment-specific token prices are configured."""
        input_rate = float(getattr(settings, "AI_INPUT_COST_PER_1M_TOKENS_USD", 0))
        output_rate = float(getattr(settings, "AI_OUTPUT_COST_PER_1M_TOKENS_USD", 0))
        if input_rate <= 0 and output_rate <= 0:
            return None
        cost = (
            usage["input_tokens"] * input_rate + usage["output_tokens"] * output_rate
        ) / 1_000_000
        return round(cost, 8)

    def _record_observation(
        self,
        *,
        operation: str,
        started_at: float,
        fallback_reason: str | None = None,
        retry_count: int = 0,
        usage: dict[str, int] | None = None,
        error: Exception | None = None,
        extra: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Create and emit a safe, structured provider observation."""
        if isinstance(error, _ProviderCallError):
            retry_count += error.retry_count
            error = error.cause
        normalized_usage = usage or self._empty_usage()
        observation: dict[str, object] = {
            "provider_observability": {
                "provider": self.provider_name,
                "model": self._config.model,
                "operation": operation,
                "status": "fallback" if fallback_reason else "succeeded",
                "latency_ms": int((time.perf_counter() - started_at) * 1000),
                "retry_count": retry_count,
                "fallback_reason": fallback_reason,
                "error_type": type(error).__name__ if error else None,
                "token_usage": normalized_usage,
                "estimated_cost_usd": self._estimated_cost_usd(normalized_usage),
                **(extra or {}),
            }
        }
        self.last_observation = observation
        event_data = cast(dict[str, object], observation["provider_observability"])
        if fallback_reason:
            logger.warning("ai_provider_fallback", **event_data)
        else:
            logger.info("ai_provider_succeeded", **event_data)
        return observation

    def _attach_observation(
        self, *, context: ToolContext, observation: dict[str, object]
    ) -> None:
        """Keep provider telemetry on the run even when orchestration falls back."""
        context.run.metadata = {**context.run.metadata, **observation}

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
