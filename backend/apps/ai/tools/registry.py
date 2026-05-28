"""Central tool registry."""

from __future__ import annotations

from time import perf_counter

from apps.ai.models import ToolExecution
from apps.ai.services.audit_service import AuditService
from apps.ai.services.approval_service import ApprovalService

from .analytics_tools import (
    get_sales_by_bottle,
    get_sales_by_varietal,
    get_sales_over_period,
    get_sales_summary,
)
from .base import ToolContext, ToolSpec
from .business_tools import (
    assign_order_issue,
    check_payment_issue,
    classify_customer_message,
    create_internal_note,
    create_lead_from_conversation,
    create_support_task,
    draft_whatsapp_reply,
    mark_order_for_review,
    recommend_wines_for_customer,
    send_support_email,
    send_whatsapp_message,
    update_lead_status,
    update_order_status,
    update_support_task,
)
from .catalog_tools import get_stock_snapshot, search_catalog
from .knowledge_tools import search_knowledge_base
from .ops_tools import list_low_stock_items, list_pending_orders
from .order_tools import get_order_by_number


class ToolRegistry:
    """Register and execute typed tools."""

    def __init__(self) -> None:
        """Populate the built-in registry."""
        self._tools = {
            spec.name: spec
            for spec in [
                ToolSpec(
                    name="get_order_by_number",
                    description="Fetch a single order by its human-readable number.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "order_number": {"type": "string", "description": "Human-readable order number such as LAB-2026-000145."}
                        },
                        "required": ["order_number"],
                        "additionalProperties": False,
                    },
                    handler=get_order_by_number,
                ),
                ToolSpec(
                    name="search_catalog",
                    description="Search the wine catalog.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Customer or operator search query for wines."}
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                    handler=search_catalog,
                ),
                ToolSpec(
                    name="get_stock_snapshot",
                    description="Get current stock for one wine.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "sku": {"type": "string"},
                            "slug": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                    handler=get_stock_snapshot,
                ),
                ToolSpec(
                    name="search_knowledge_base",
                    description="Search the AI knowledge base.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Question to answer from La Abeja knowledge."}
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                    handler=search_knowledge_base,
                ),
                ToolSpec(
                    name="list_low_stock_items",
                    description="List wines with low stock.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "minimum": 1, "maximum": 20}
                        },
                        "additionalProperties": False,
                    },
                    handler=list_low_stock_items,
                ),
                ToolSpec(
                    name="list_pending_orders",
                    description="List pending operational orders.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "minimum": 1, "maximum": 20}
                        },
                        "additionalProperties": False,
                    },
                    handler=list_pending_orders,
                ),
                ToolSpec(
                    name="classify_customer_message",
                    description="Classify a customer message into support, payment, sales, or booking intents.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "Raw customer message text."}
                        },
                        "required": ["message"],
                        "additionalProperties": False,
                    },
                    handler=classify_customer_message,
                ),
                ToolSpec(
                    name="draft_whatsapp_reply",
                    description="Draft a WhatsApp response without sending it.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "Customer message to answer."},
                            "customer_name": {"type": "string", "description": "Optional customer first or full name."},
                        },
                        "required": ["message"],
                        "additionalProperties": False,
                    },
                    handler=draft_whatsapp_reply,
                ),
                ToolSpec(
                    name="recommend_wines_for_customer",
                    description="Recommend wines using customer preferences, varietal hints, and price range.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "customer_email": {"type": "string"},
                            "preferred_varietals": {"type": "array", "items": {"type": "string"}},
                            "min_price": {"type": "number"},
                            "max_price": {"type": "number"},
                            "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                        },
                        "additionalProperties": False,
                    },
                    handler=recommend_wines_for_customer,
                ),
                ToolSpec(
                    name="check_payment_issue",
                    description="Inspect a payment or order and explain the likely payment issue.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "order_number": {"type": "string"},
                            "mp_payment_id": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                    handler=check_payment_issue,
                ),
                ToolSpec(
                    name="create_support_task",
                    description="Create an internal support or operations follow-up task.",
                    risk_level=ToolExecution.RiskLevel.LOW_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "task_type": {
                                "type": "string",
                                "enum": [
                                    "support_follow_up",
                                    "order_issue",
                                    "order_review",
                                    "payment_review",
                                    "lead_follow_up",
                                ],
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "urgent"],
                            },
                            "order_number": {"type": "string"},
                            "conversation_id": {"type": "string"},
                            "customer_email": {"type": "string"},
                            "assigned_to_email": {"type": "string"},
                            "due_at": {"type": "string"},
                            "due_in_days": {"type": "integer"},
                        },
                        "required": ["title"],
                        "additionalProperties": False,
                    },
                    handler=create_support_task,
                ),
                ToolSpec(
                    name="create_internal_note",
                    description="Persist an internal note linked to a customer, conversation, or order.",
                    risk_level=ToolExecution.RiskLevel.LOW_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "note_type": {
                                "type": "string",
                                "enum": ["general", "order", "customer", "support", "sales", "payment"],
                            },
                            "order_number": {"type": "string"},
                            "conversation_id": {"type": "string"},
                            "customer_email": {"type": "string"},
                        },
                        "required": ["content"],
                        "additionalProperties": False,
                    },
                    handler=create_internal_note,
                ),
                ToolSpec(
                    name="update_support_task",
                    description="Update an internal AI-generated task status, assignee, or due date.",
                    risk_level=ToolExecution.RiskLevel.LOW_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["open", "in_progress", "blocked", "completed", "cancelled"],
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "urgent"],
                            },
                            "assigned_to_email": {"type": "string"},
                            "due_at": {"type": "string"},
                            "due_in_days": {"type": "integer"},
                            "append_note": {"type": "string"},
                        },
                        "required": ["task_id"],
                        "additionalProperties": False,
                    },
                    handler=update_support_task,
                ),
                ToolSpec(
                    name="assign_order_issue",
                    description="Create an internal issue task for a problematic order.",
                    risk_level=ToolExecution.RiskLevel.LOW_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "order_number": {"type": "string"},
                            "issue_type": {"type": "string"},
                            "summary": {"type": "string"},
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "urgent"],
                            },
                            "assigned_to_email": {"type": "string"},
                        },
                        "required": ["order_number", "summary"],
                        "additionalProperties": False,
                    },
                    handler=assign_order_issue,
                ),
                ToolSpec(
                    name="mark_order_for_review",
                    description="Mark an order for manual review by creating a high-priority internal task.",
                    risk_level=ToolExecution.RiskLevel.LOW_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "order_number": {"type": "string"},
                            "reason": {"type": "string"},
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "urgent"],
                            },
                        },
                        "required": ["order_number", "reason"],
                        "additionalProperties": False,
                    },
                    handler=mark_order_for_review,
                ),
                ToolSpec(
                    name="create_lead_from_conversation",
                    description="Create a commercial lead from a conversation or captured contact data.",
                    risk_level=ToolExecution.RiskLevel.LOW_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "full_name": {"type": "string"},
                            "email": {"type": "string"},
                            "phone": {"type": "string"},
                            "company": {"type": "string"},
                            "interest_summary": {"type": "string"},
                            "desired_varietals": {"type": "array", "items": {"type": "string"}},
                            "estimated_order_value": {"type": "number"},
                            "conversation_id": {"type": "string"},
                            "customer_email": {"type": "string"},
                            "source_channel": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                    handler=create_lead_from_conversation,
                ),
                ToolSpec(
                    name="update_lead_status",
                    description="Update the qualification status or commercial estimate of an existing lead.",
                    risk_level=ToolExecution.RiskLevel.LOW_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "lead_id": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["new", "qualified", "contacted", "converted", "lost"],
                            },
                            "interest_summary": {"type": "string"},
                            "estimated_order_value": {"type": "number"},
                        },
                        "required": ["lead_id"],
                        "additionalProperties": False,
                    },
                    handler=update_lead_status,
                ),
                ToolSpec(
                    name="update_order_status",
                    description="Change a real order status, tracking number, or estimated delivery.",
                    risk_level=ToolExecution.RiskLevel.HIGH_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "order_number": {"type": "string"},
                            "new_status": {
                                "type": "string",
                                "enum": [
                                    "pending_payment",
                                    "payment_failed",
                                    "paid",
                                    "preparing",
                                    "ready_to_ship",
                                    "shipped",
                                    "delivered",
                                    "cancelled",
                                    "refunded",
                                ],
                            },
                            "tracking_number": {"type": "string"},
                            "estimated_delivery": {"type": "string"},
                            "note": {"type": "string"},
                        },
                        "required": ["order_number", "new_status"],
                        "additionalProperties": False,
                    },
                    handler=update_order_status,
                    requires_approval=True,
                ),
                ToolSpec(
                    name="send_whatsapp_message",
                    description="Send a real WhatsApp message to a customer.",
                    risk_level=ToolExecution.RiskLevel.HIGH_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "phone": {"type": "string"},
                            "customer_email": {"type": "string"},
                            "order_number": {"type": "string"},
                            "conversation_id": {"type": "string"},
                            "message": {"type": "string"},
                            "template": {"type": "string"},
                            "params": {"type": "array", "items": {"type": "string"}},
                        },
                        "additionalProperties": False,
                    },
                    handler=send_whatsapp_message,
                    requires_approval=True,
                ),
                ToolSpec(
                    name="send_support_email",
                    description="Send a real support or sales follow-up email to a customer.",
                    risk_level=ToolExecution.RiskLevel.HIGH_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "to": {"type": "string"},
                            "customer_email": {"type": "string"},
                            "order_number": {"type": "string"},
                            "conversation_id": {"type": "string"},
                            "template": {"type": "string"},
                            "subject_hint": {"type": "string"},
                            "message": {"type": "string"},
                        },
                        "required": ["message"],
                        "additionalProperties": False,
                    },
                    handler=send_support_email,
                    requires_approval=True,
                ),
                ToolSpec(
                    name="get_sales_summary",
                    description="Return total sales, revenue, average order value, and sold bottles for a date window.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "period": {"type": "string", "enum": ["last_7_days", "last_30_days", "current_month", "previous_month"]},
                        },
                        "additionalProperties": False,
                    },
                    handler=get_sales_summary,
                ),
                ToolSpec(
                    name="get_sales_over_period",
                    description="Group sales counts, revenue, and sold bottles by day, week, or month.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "period": {"type": "string", "enum": ["last_7_days", "last_30_days", "current_month", "previous_month"]},
                            "grain": {"type": "string", "enum": ["day", "week", "month"]},
                        },
                        "additionalProperties": False,
                    },
                    handler=get_sales_over_period,
                ),
                ToolSpec(
                    name="get_sales_by_varietal",
                    description="Aggregate sold bottles and revenue by varietal.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "period": {"type": "string", "enum": ["last_7_days", "last_30_days", "current_month", "previous_month"]},
                            "limit": {"type": "integer", "minimum": 1, "maximum": 25},
                        },
                        "additionalProperties": False,
                    },
                    handler=get_sales_by_varietal,
                ),
                ToolSpec(
                    name="get_sales_by_bottle",
                    description="Aggregate sold bottles and revenue by wine SKU and label.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "period": {"type": "string", "enum": ["last_7_days", "last_30_days", "current_month", "previous_month"]},
                            "limit": {"type": "integer", "minimum": 1, "maximum": 25},
                        },
                        "additionalProperties": False,
                    },
                    handler=get_sales_by_bottle,
                ),
            ]
        }
        self._audit_service = AuditService()
        self._approval_service = ApprovalService()

    def execute(
        self,
        *,
        tool_name: str,
        payload: dict[str, object],
        context: ToolContext,
        bypass_approval: bool = False,
    ) -> dict[str, object]:
        """Execute a registered tool and audit the result."""
        spec = self._tools[tool_name]
        started_at = perf_counter()
        if spec.requires_approval and not bypass_approval:
            approval = self._approval_service.request_tool_approval(spec=spec, payload=payload, context=context)
            latency_ms = int((perf_counter() - started_at) * 1000)
            result = {
                "approval_required": True,
                "action_name": spec.name,
                "approval_request_id": str(approval.id),
                "workflow_run_id": str(approval.workflow_run_id),
                "summary": approval.action_payload.get("summary", ""),
                "message": "Se requiere aprobacion humana antes de ejecutar esta accion.",
            }
            self._audit_service.log_tool_execution(
                run=context.run,
                tool_name=tool_name,
                risk_level=spec.risk_level,
                input_payload=payload,
                output_payload=result,
                latency_ms=latency_ms,
                status=ToolExecution.Status.BLOCKED,
            )
            pending_approvals = list(context.run.metadata.get("pending_approval_ids", []))
            pending_approvals.append(str(approval.id))
            context.run.needs_human = True
            context.run.metadata = {
                **context.run.metadata,
                "pending_approval_ids": pending_approvals,
            }
            context.run.save(update_fields=["needs_human", "metadata", "updated_at"])
            return result
        try:
            result = spec.handler(payload, context)
            latency_ms = int((perf_counter() - started_at) * 1000)
            self._audit_service.log_tool_execution(
                run=context.run,
                tool_name=tool_name,
                risk_level=spec.risk_level,
                input_payload=payload,
                output_payload=result,
                latency_ms=latency_ms,
                status=ToolExecution.Status.SUCCEEDED,
            )
            return result
        except Exception as exc:
            latency_ms = int((perf_counter() - started_at) * 1000)
            self._audit_service.log_tool_execution(
                run=context.run,
                tool_name=tool_name,
                risk_level=spec.risk_level,
                input_payload=payload,
                output_payload={},
                latency_ms=latency_ms,
                status=ToolExecution.Status.FAILED,
                error=str(exc),
            )
            raise

    def get_tool_definitions(self, tool_names: list[str] | None = None) -> list[dict[str, object]]:
        """Return OpenAI-compatible tool definitions for the selected tools."""
        names = tool_names or list(self._tools.keys())
        return [
            {
                "type": "function",
                "name": spec.name,
                "description": spec.description,
                "strict": True,
                "parameters": spec.input_schema,
            }
            for spec in (self._tools[name] for name in names if name in self._tools)
        ]

    def has_tool(self, tool_name: str) -> bool:
        """Return whether a tool is registered."""
        return tool_name in self._tools
