"""Central tool registry."""

# ruff: noqa: E501

from __future__ import annotations

from time import perf_counter

from apps.ai.models import ToolExecution
from apps.ai.services.approval_service import ApprovalService
from apps.ai.services.audit_service import AuditService

from .analytics_tools import (
    get_conversion_funnel,
    get_margin_estimate_by_product,
    get_repeat_customers_metrics,
    get_returns_and_incidents_metrics,
    get_sales_by_bottle,
    get_sales_by_channel,
    get_sales_by_varietal,
    get_sales_over_period,
    get_sales_summary,
    get_top_skus,
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
from .knowledge_tools import (
    get_answerable_sources,
    search_knowledge_base,
    search_playbooks,
    search_policies,
)
from .operations_tools import (
    create_payment_followup,
    create_restock_task,
    create_shipping_claim,
    create_ticket_and_assign,
    escalate_conversation_to_human,
    generate_shipping_update,
    get_customer_360,
    get_customer_orders_summary,
    release_stock_reservation,
    request_order_cancellation,
    reserve_stock,
    search_internal_notes,
    search_orders,
    sync_tracking_status,
)
from .ops_tools import list_low_stock_items, list_pending_orders
from .order_tools import get_order_by_number
from .visit_tools import search_visit_context


class ToolRegistry:
    """Register and execute typed tools."""

    def __init__(self) -> None:
        """Populate the built-in registry."""
        self._tools = {
            spec.name: spec
            for spec in [
                ToolSpec(
                    name="search_visit_context",
                    description="Search winery visits, events, slots, and bookings.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "status": {"type": "string"},
                            "experience_id": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                        },
                        "additionalProperties": False,
                    },
                    handler=search_visit_context,
                ),
                ToolSpec(
                    name="get_order_by_number",
                    description="Fetch a single order by its human-readable number.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "order_number": {
                                "type": "string",
                                "description": "Human-readable order number such as LAB-2026-000145.",
                            }
                        },
                        "required": ["order_number"],
                        "additionalProperties": False,
                    },
                    handler=get_order_by_number,
                ),
                ToolSpec(
                    name="search_orders",
                    description="Search orders by customer, status, free text, or date window.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "customer_email": {"type": "string"},
                            "phone": {"type": "string"},
                            "status": {"type": "string"},
                            "statuses": {"type": "array", "items": {"type": "string"}},
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "period": {
                                "type": "string",
                                "enum": [
                                    "last_7_days",
                                    "last_30_days",
                                    "current_month",
                                    "previous_month",
                                ],
                            },
                            "limit": {"type": "integer", "minimum": 1, "maximum": 25},
                        },
                        "additionalProperties": False,
                    },
                    handler=search_orders,
                ),
                ToolSpec(
                    name="search_catalog",
                    description="Search the wine catalog.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Customer or operator search query for wines.",
                            }
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
                            "query": {
                                "type": "string",
                                "description": "Question to answer from La Abeja knowledge.",
                            }
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                    handler=search_knowledge_base,
                ),
                ToolSpec(
                    name="search_policies",
                    description="Search policies such as shipping, pickup, payment, and return guidance.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                    handler=search_policies,
                ),
                ToolSpec(
                    name="search_playbooks",
                    description="Search internal playbooks and SOP-style operational guidance.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                    handler=search_playbooks,
                ),
                ToolSpec(
                    name="get_answerable_sources",
                    description="List the source documents that best support an answer for a query.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                    handler=get_answerable_sources,
                ),
                ToolSpec(
                    name="list_low_stock_items",
                    description="List wines with low stock.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20}},
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
                        "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20}},
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
                            "message": {
                                "type": "string",
                                "description": "Raw customer message text.",
                            }
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
                            "message": {
                                "type": "string",
                                "description": "Customer message to answer.",
                            },
                            "customer_name": {
                                "type": "string",
                                "description": "Optional customer first or full name.",
                            },
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
                    name="get_customer_orders_summary",
                    description="Return a concise order history summary for one customer.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "customer_email": {"type": "string"},
                            "order_number": {"type": "string"},
                            "conversation_id": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                    handler=get_customer_orders_summary,
                ),
                ToolSpec(
                    name="get_customer_360",
                    description="Return a staff-facing 360 profile including orders, tasks, notes, and leads.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "customer_email": {"type": "string"},
                            "order_number": {"type": "string"},
                            "conversation_id": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                    handler=get_customer_360,
                ),
                ToolSpec(
                    name="search_internal_notes",
                    description="Search internal notes by customer, order, conversation, type, or free text.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "order_number": {"type": "string"},
                            "customer_email": {"type": "string"},
                            "conversation_id": {"type": "string"},
                            "note_type": {
                                "type": "string",
                                "enum": [
                                    "general",
                                    "order",
                                    "customer",
                                    "support",
                                    "sales",
                                    "payment",
                                ],
                            },
                            "limit": {"type": "integer", "minimum": 1, "maximum": 25},
                        },
                        "additionalProperties": False,
                    },
                    handler=search_internal_notes,
                ),
                ToolSpec(
                    name="generate_shipping_update",
                    description="Generate a customer-facing shipping update without sending it.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "order_number": {"type": "string"},
                        },
                        "required": ["order_number"],
                        "additionalProperties": False,
                    },
                    handler=generate_shipping_update,
                ),
                ToolSpec(
                    name="sync_tracking_status",
                    description="Return the best available tracking snapshot for an order and its current carrier hint.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "order_number": {"type": "string"},
                        },
                        "required": ["order_number"],
                        "additionalProperties": False,
                    },
                    handler=sync_tracking_status,
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
                    name="create_ticket_and_assign",
                    description="Create a ticket-style internal task with explicit ownership.",
                    risk_level=ToolExecution.RiskLevel.LOW_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "summary": {"type": "string"},
                            "ticket_type": {"type": "string"},
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
                        "required": ["summary"],
                        "additionalProperties": False,
                    },
                    handler=create_ticket_and_assign,
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
                                "enum": [
                                    "general",
                                    "order",
                                    "customer",
                                    "support",
                                    "sales",
                                    "payment",
                                ],
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
                    name="escalate_conversation_to_human",
                    description="Escalate a conversation to the human team and create a follow-up task.",
                    risk_level=ToolExecution.RiskLevel.LOW_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "conversation_id": {"type": "string"},
                            "title": {"type": "string"},
                            "reason": {"type": "string"},
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "urgent"],
                            },
                            "assigned_to_email": {"type": "string"},
                            "due_in_days": {"type": "integer"},
                            "customer_email": {"type": "string"},
                        },
                        "required": ["reason"],
                        "additionalProperties": False,
                    },
                    handler=escalate_conversation_to_human,
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
                                "enum": [
                                    "open",
                                    "in_progress",
                                    "blocked",
                                    "completed",
                                    "cancelled",
                                ],
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
                    name="create_payment_followup",
                    description="Create a payment-review task and internal note from a payment issue.",
                    risk_level=ToolExecution.RiskLevel.LOW_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "order_number": {"type": "string"},
                            "mp_payment_id": {"type": "string"},
                            "summary": {"type": "string"},
                            "customer_email": {"type": "string"},
                            "assigned_to_email": {"type": "string"},
                            "due_in_days": {"type": "integer"},
                        },
                        "additionalProperties": False,
                    },
                    handler=create_payment_followup,
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
                    name="create_shipping_claim",
                    description="Create a shipping-claim task and internal note for a delayed or problematic order.",
                    risk_level=ToolExecution.RiskLevel.LOW_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "order_number": {"type": "string"},
                            "claim_reason": {"type": "string"},
                            "summary": {"type": "string"},
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "urgent"],
                            },
                            "assigned_to_email": {"type": "string"},
                            "due_in_days": {"type": "integer"},
                        },
                        "required": ["order_number", "claim_reason", "summary"],
                        "additionalProperties": False,
                    },
                    handler=create_shipping_claim,
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
                    name="create_restock_task",
                    description="Create a restock task for one low-stock wine.",
                    risk_level=ToolExecution.RiskLevel.LOW_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "sku": {"type": "string"},
                            "slug": {"type": "string"},
                            "auto_low_stock": {"type": "boolean"},
                            "suggested_quantity": {"type": "integer"},
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "urgent"],
                            },
                            "assigned_to_email": {"type": "string"},
                            "due_in_days": {"type": "integer"},
                        },
                        "additionalProperties": False,
                    },
                    handler=create_restock_task,
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
                    name="reserve_stock",
                    description="Reserve inventory for a wine by decrementing available stock and persisting a reservation record.",
                    risk_level=ToolExecution.RiskLevel.HIGH_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "sku": {"type": "string"},
                            "slug": {"type": "string"},
                            "quantity": {"type": "integer"},
                            "order_number": {"type": "string"},
                            "conversation_id": {"type": "string"},
                            "customer_email": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                        "required": ["quantity"],
                        "additionalProperties": False,
                    },
                    handler=reserve_stock,
                    requires_approval=True,
                ),
                ToolSpec(
                    name="release_stock_reservation",
                    description="Release a full or partial stock reservation and restore inventory.",
                    risk_level=ToolExecution.RiskLevel.HIGH_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "reservation_id": {"type": "string"},
                            "quantity": {"type": "integer"},
                        },
                        "required": ["reservation_id"],
                        "additionalProperties": False,
                    },
                    handler=release_stock_reservation,
                    requires_approval=True,
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
                    name="request_order_cancellation",
                    description="Cancel an order after approval, and create any needed financial follow-up task.",
                    risk_level=ToolExecution.RiskLevel.HIGH_RISK_WRITE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "order_number": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                        "required": ["order_number", "reason"],
                        "additionalProperties": False,
                    },
                    handler=request_order_cancellation,
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
                            "period": {
                                "type": "string",
                                "enum": [
                                    "last_7_days",
                                    "last_30_days",
                                    "current_month",
                                    "previous_month",
                                ],
                            },
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
                            "period": {
                                "type": "string",
                                "enum": [
                                    "last_7_days",
                                    "last_30_days",
                                    "current_month",
                                    "previous_month",
                                ],
                            },
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
                            "period": {
                                "type": "string",
                                "enum": [
                                    "last_7_days",
                                    "last_30_days",
                                    "current_month",
                                    "previous_month",
                                ],
                            },
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
                            "period": {
                                "type": "string",
                                "enum": [
                                    "last_7_days",
                                    "last_30_days",
                                    "current_month",
                                    "previous_month",
                                ],
                            },
                            "limit": {"type": "integer", "minimum": 1, "maximum": 25},
                        },
                        "additionalProperties": False,
                    },
                    handler=get_sales_by_bottle,
                ),
                ToolSpec(
                    name="get_top_skus",
                    description="Return the best-performing SKUs by units, revenue, or order count.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "period": {
                                "type": "string",
                                "enum": [
                                    "last_7_days",
                                    "last_30_days",
                                    "current_month",
                                    "previous_month",
                                ],
                            },
                            "sort_by": {
                                "type": "string",
                                "enum": ["bottles_sold", "revenue", "order_count"],
                            },
                            "limit": {"type": "integer", "minimum": 1, "maximum": 25},
                        },
                        "additionalProperties": False,
                    },
                    handler=get_top_skus,
                ),
                ToolSpec(
                    name="get_repeat_customers_metrics",
                    description="Estimate repeat-customer and retention-style metrics from completed orders.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "period": {
                                "type": "string",
                                "enum": [
                                    "last_7_days",
                                    "last_30_days",
                                    "current_month",
                                    "previous_month",
                                ],
                            },
                        },
                        "additionalProperties": False,
                    },
                    handler=get_repeat_customers_metrics,
                ),
                ToolSpec(
                    name="get_conversion_funnel",
                    description="Estimate a simple cart-to-order-to-paid funnel for a date window.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "period": {
                                "type": "string",
                                "enum": [
                                    "last_7_days",
                                    "last_30_days",
                                    "current_month",
                                    "previous_month",
                                ],
                            },
                        },
                        "additionalProperties": False,
                    },
                    handler=get_conversion_funnel,
                ),
                ToolSpec(
                    name="get_returns_and_incidents_metrics",
                    description="Summarize refunds, cancellations, payment failures, and AI-generated incident workload.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "period": {
                                "type": "string",
                                "enum": [
                                    "last_7_days",
                                    "last_30_days",
                                    "current_month",
                                    "previous_month",
                                ],
                            },
                        },
                        "additionalProperties": False,
                    },
                    handler=get_returns_and_incidents_metrics,
                ),
                ToolSpec(
                    name="get_sales_by_channel",
                    description="Aggregate completed orders by captured source channel.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "period": {
                                "type": "string",
                                "enum": [
                                    "last_7_days",
                                    "last_30_days",
                                    "current_month",
                                    "previous_month",
                                ],
                            },
                        },
                        "additionalProperties": False,
                    },
                    handler=get_sales_by_channel,
                ),
                ToolSpec(
                    name="get_margin_estimate_by_product",
                    description="Estimate revenue, cost, and margin by sold product.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "period": {
                                "type": "string",
                                "enum": [
                                    "last_7_days",
                                    "last_30_days",
                                    "current_month",
                                    "previous_month",
                                ],
                            },
                            "limit": {"type": "integer", "minimum": 1, "maximum": 25},
                        },
                        "additionalProperties": False,
                    },
                    handler=get_margin_estimate_by_product,
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
            approval = self._approval_service.request_tool_approval(
                spec=spec, payload=payload, context=context
            )
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
