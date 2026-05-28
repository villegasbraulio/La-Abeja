"""Approval orchestration for risky AI actions."""

from __future__ import annotations

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.ai.models import AgentRun, ApprovalRequest, Conversation, WorkflowRun
from apps.ai.tools.base import ToolContext, ToolSpec

user_model = get_user_model()


class ApprovalService:
    """Create and execute approval-gated tool actions."""

    @transaction.atomic
    def request_tool_approval(
        self,
        *,
        spec: ToolSpec,
        payload: dict[str, object],
        context: ToolContext,
    ) -> ApprovalRequest:
        """Persist a pending approval for a high-risk tool."""
        workflow = WorkflowRun.objects.create(
            workflow_type="tool_approval",
            status=WorkflowRun.Status.PENDING,
            actor_type="staff" if context.is_staff else "customer",
            input_payload={
                "tool_name": spec.name,
                "tool_description": spec.description,
                "tool_payload": payload,
                "conversation_id": str(context.run.conversation_id) if context.run.conversation_id else None,
                "requested_run_id": str(context.run.id),
                "requested_by_user_id": context.user_id,
                "risk_level": spec.risk_level,
            },
            result_payload={},
            idempotency_key=f"tool-approval:{spec.name}:{context.run.id}:{uuid4()}",
        )
        return ApprovalRequest.objects.create(
            workflow_run=workflow,
            action_name=spec.name,
            action_payload={
                "tool_name": spec.name,
                "tool_description": spec.description,
                "tool_payload": payload,
                "conversation_id": str(context.run.conversation_id) if context.run.conversation_id else None,
                "requested_run_id": str(context.run.id),
                "requested_by_user_id": context.user_id,
                "risk_level": spec.risk_level,
                "summary": self._build_summary(spec=spec, payload=payload),
            },
        )

    @transaction.atomic
    def approve(
        self,
        *,
        approval: ApprovalRequest,
        approved_by: object,
        note: str = "",
    ) -> ApprovalRequest:
        """Approve and execute a pending tool action."""
        if approval.status != ApprovalRequest.Status.PENDING:
            return approval

        workflow = approval.workflow_run
        workflow.status = WorkflowRun.Status.RUNNING
        workflow.result_payload = {}
        workflow.save(update_fields=["status", "result_payload", "updated_at"])

        action_payload = dict(approval.action_payload or {})
        tool_name = str(action_payload.get("tool_name") or approval.action_name)
        payload = action_payload.get("tool_payload")
        tool_payload = payload if isinstance(payload, dict) else dict(action_payload)

        conversation = self._resolve_conversation(action_payload)
        run = AgentRun.objects.create(
            conversation=conversation,
            agent_type=AgentRun.AgentType.WORKFLOW,
            intent=tool_name,
            message_text=f"Approved action execution for {tool_name}",
            metadata={
                "approval_request_id": str(approval.id),
                "workflow_run_id": str(workflow.id),
                "approved_by_user_id": str(getattr(approved_by, "id", "")),
                "approval_execution": True,
            },
        )

        from apps.ai.tools.registry import ToolRegistry

        registry = ToolRegistry()
        try:
            result = registry.execute(
                tool_name=tool_name,
                payload=tool_payload,
                context=ToolContext(
                    run=run,
                    user_id=str(getattr(approved_by, "id", "")) or None,
                    is_staff=bool(getattr(approved_by, "is_staff", False)),
                ),
                bypass_approval=True,
            )
            run.status = AgentRun.Status.COMPLETED
            run.response_text = f"Approved action executed: {tool_name}"
            run.needs_human = False
            run.save(update_fields=["status", "response_text", "needs_human", "updated_at"])

            workflow.status = WorkflowRun.Status.COMPLETED
            workflow.result_payload = {
                "tool_name": tool_name,
                "tool_result": result,
                "executed_run_id": str(run.id),
            }
            workflow.save(update_fields=["status", "result_payload", "updated_at"])

            action_payload["execution_status"] = "succeeded"
            action_payload["execution_result"] = result
            action_payload["executed_run_id"] = str(run.id)
        except Exception as exc:
            run.status = AgentRun.Status.FAILED
            run.response_text = str(exc)
            run.needs_human = True
            run.save(update_fields=["status", "response_text", "needs_human", "updated_at"])

            workflow.status = WorkflowRun.Status.FAILED
            workflow.result_payload = {
                "tool_name": tool_name,
                "error": str(exc),
                "executed_run_id": str(run.id),
            }
            workflow.save(update_fields=["status", "result_payload", "updated_at"])

            action_payload["execution_status"] = "failed"
            action_payload["execution_error"] = str(exc)
            action_payload["executed_run_id"] = str(run.id)

        approval.status = ApprovalRequest.Status.APPROVED
        approval.approved_by = approved_by if isinstance(approved_by, user_model) else None
        approval.decision_note = note
        approval.decided_at = timezone.now()
        approval.action_payload = action_payload
        approval.save(
            update_fields=["status", "approved_by", "decision_note", "decided_at", "action_payload"]
        )
        return approval

    @transaction.atomic
    def reject(
        self,
        *,
        approval: ApprovalRequest,
        approved_by: object,
        note: str = "",
    ) -> ApprovalRequest:
        """Reject a pending tool action and cancel its workflow."""
        if approval.status != ApprovalRequest.Status.PENDING:
            return approval

        workflow = approval.workflow_run
        workflow.status = WorkflowRun.Status.CANCELLED
        workflow.result_payload = {"rejected": True, "decision_note": note}
        workflow.save(update_fields=["status", "result_payload", "updated_at"])

        action_payload = dict(approval.action_payload or {})
        action_payload["execution_status"] = "rejected"

        approval.status = ApprovalRequest.Status.REJECTED
        approval.approved_by = approved_by if isinstance(approved_by, user_model) else None
        approval.decision_note = note
        approval.decided_at = timezone.now()
        approval.action_payload = action_payload
        approval.save(
            update_fields=["status", "approved_by", "decision_note", "decided_at", "action_payload"]
        )
        return approval

    def _build_summary(self, *, spec: ToolSpec, payload: dict[str, object]) -> str:
        """Build a concise operator-facing summary for the approval queue."""
        bits = []
        if payload.get("order_number"):
            bits.append(f"pedido {payload['order_number']}")
        if payload.get("customer_email"):
            bits.append(f"cliente {payload['customer_email']}")
        if payload.get("phone"):
            bits.append(f"telefono {payload['phone']}")
        if payload.get("new_status"):
            bits.append(f"estado destino {payload['new_status']}")
        if payload.get("message"):
            bits.append(f"mensaje: {str(payload['message'])[:100]}")
        return f"{spec.description} {' | '.join(bits)}".strip()

    def _resolve_conversation(self, action_payload: dict[str, object]) -> Conversation | None:
        """Resolve the original conversation when available."""
        conversation_id = str(action_payload.get("conversation_id") or "").strip()
        if not conversation_id:
            return None
        return Conversation.objects.filter(id=conversation_id).first()
