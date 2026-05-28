"""Prompt regression tests for the AI app."""

from __future__ import annotations

from apps.ai.agents.prompt_manager import PromptManager


def test_support_prompt_keeps_core_grounding_and_safety_clauses() -> None:
    """Support prompt should preserve anti-hallucination and guidance invariants."""
    prompt = PromptManager().support_prompt()

    required_fragments = [
        "Rioplatense Spanish",
        "Use tool data as source of truth for live business state",
        "Use retrieved knowledge only for policies, FAQs, and guidance",
        "Do not invent order status, stock, payment state, pricing, or shipping timelines",
        "prefer recommend_wines_for_customer or search_catalog",
        "prefer check_payment_issue",
        "If evidence is insufficient, say so clearly",
        "Do not claim an action was executed unless a tool result confirms it",
    ]
    for fragment in required_fragments:
        assert fragment in prompt


def test_ops_prompt_keeps_write_and_approval_guardrails() -> None:
    """Ops prompt should preserve write gating and approval explanations."""
    prompt = PromptManager().ops_prompt()

    required_fragments = [
        "Always answer in concise, operational Spanish",
        "Prefer tools over free-text reasoning whenever a live tool exists",
        "Use search_knowledge_base for policies or internal playbooks, not for live business state",
        "Use reserve_stock, release_stock_reservation, update_order_status, request_order_cancellation, send_whatsapp_message, or send_support_email only when the operator explicitly requests a real state change",
        "High-risk write tools can return approval_required=true",
        "mention the approval_request_id",
        "Never imply a write action happened if it did not",
        "ask for the missing business identifier such as order number, customer email, assignee email, phone, or period",
    ]
    for fragment in required_fragments:
        assert fragment in prompt
