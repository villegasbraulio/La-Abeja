"""Approval orchestration for risky AI actions."""

# ruff: noqa: E501

from __future__ import annotations

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.ai.models import AgentRun, ApprovalRequest, Conversation, WorkflowRun
from apps.ai.tools.base import ToolContext, ToolSpec
from apps.orders.models import Order

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
                "conversation_id": str(context.run.conversation_id)
                if context.run.conversation_id
                else None,
                "requested_run_id": str(context.run.id),
                "requested_by_user_id": str(context.user_id) if context.user_id else None,
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
                "conversation_id": str(context.run.conversation_id)
                if context.run.conversation_id
                else None,
                "requested_run_id": str(context.run.id),
                "requested_by_user_id": str(context.user_id) if context.user_id else None,
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
                    user_id=getattr(approved_by, "id", None),
                    is_staff=bool(getattr(approved_by, "is_staff", False)),
                ),
                bypass_approval=True,
            )
            run.status = AgentRun.Status.COMPLETED
            run.response_text = f"Approved action executed: {tool_name}"
            run.needs_human = False
            run.save(update_fields=["status", "response_text", "needs_human", "updated_at"])

            post_approval_suggestion = self._build_post_approval_suggestion(
                tool_name=tool_name,
                payload=tool_payload,
                result=result,
            )
            workflow.status = WorkflowRun.Status.COMPLETED
            workflow.result_payload = {
                "tool_name": tool_name,
                "tool_result": result,
                "executed_run_id": str(run.id),
            }
            if post_approval_suggestion:
                workflow.result_payload["post_approval_suggestion"] = post_approval_suggestion
            workflow.save(update_fields=["status", "result_payload", "updated_at"])

            action_payload["execution_status"] = "succeeded"
            action_payload["execution_result"] = result
            action_payload["executed_run_id"] = str(run.id)
            if post_approval_suggestion:
                action_payload["post_approval_suggestion"] = post_approval_suggestion
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

    def _build_post_approval_suggestion(
        self,
        *,
        tool_name: str,
        payload: dict[str, object],
        result: dict[str, object],
    ) -> dict[str, object] | None:
        """Return a deterministic next-step suggestion after a risky action succeeds."""
        if tool_name == "update_order_status":
            return self._build_order_status_suggestion(payload=payload, result=result)
        if tool_name == "request_order_cancellation":
            return self._build_cancellation_suggestion(payload=payload, result=result)
        if tool_name == "reserve_stock":
            return self._build_reservation_suggestion(payload=payload, result=result)
        return None

    def _build_order_status_suggestion(
        self,
        *,
        payload: dict[str, object],
        result: dict[str, object],
    ) -> dict[str, object] | None:
        """Create the recommended follow-up after a status change."""
        order_number = str(result.get("order_number") or payload.get("order_number") or "").strip()
        status_value = str(result.get("status") or payload.get("new_status") or "").strip()
        tracking_number = str(
            result.get("tracking_number") or payload.get("tracking_number") or ""
        ).strip()
        estimated_delivery = str(
            result.get("estimated_delivery") or payload.get("estimated_delivery") or ""
        ).strip()

        if not order_number or not status_value:
            return None

        tracking_fragment = f" con tracking {tracking_number}" if tracking_number else ""
        delivery_fragment = (
            f" y entrega estimada {estimated_delivery}" if estimated_delivery else ""
        )

        if status_value == Order.Status.SHIPPED:
            return {
                "kind": "customer_message",
                "title": "Avisar despacho al cliente",
                "summary": (
                    f"El pedido {order_number} ya quedó despachado. Conviene avisarle al cliente"
                    " con el tracking y la fecha estimada."
                ),
                "suggested_message": (
                    f"Hola, tu pedido {order_number} ya fue despachado{tracking_fragment}"
                    f"{delivery_fragment}. Si necesitás ayuda con la entrega, respondé este mensaje."
                ),
                "suggested_prompt": (
                    f"Mandale un WhatsApp al cliente del pedido {order_number} avisando que ya fue"
                    f" despachado{tracking_fragment}{delivery_fragment}."
                ),
            }
        if status_value == Order.Status.DELIVERED:
            return {
                "kind": "customer_message",
                "title": "Confirmar entrega",
                "summary": (
                    f"El pedido {order_number} ya figura entregado. Podés confirmar la entrega"
                    " y abrir espacio para feedback o incidencia."
                ),
                "suggested_message": (
                    f"Hola, vemos el pedido {order_number} como entregado. Queríamos confirmar"
                    " que haya llegado bien y quedamos atentos si necesitás algo más."
                ),
                "suggested_prompt": (
                    f"Mandale un WhatsApp al cliente del pedido {order_number} para confirmar que"
                    " recibió bien la entrega."
                ),
            }
        if status_value == Order.Status.READY_TO_SHIP:
            return {
                "kind": "internal_follow_up",
                "title": "Coordinar salida o retiro",
                "summary": (
                    f"El pedido {order_number} ya está listo para salir. Conviene definir si se"
                    " despacha hoy o si hay que coordinar retiro."
                ),
                "suggested_message": (
                    f"Pedido {order_number} listo para enviar o coordinar retiro. Revisar"
                    " ventana operativa y confirmar próximo movimiento."
                ),
                "suggested_prompt": (
                    f"Creá una nota interna para el pedido {order_number} indicando que quedó listo"
                    " para despacho o coordinación de retiro."
                ),
            }
        if status_value == Order.Status.CANCELLED:
            return self._build_cancellation_suggestion(payload=payload, result=result)
        return None

    def _build_cancellation_suggestion(
        self,
        *,
        payload: dict[str, object],
        result: dict[str, object],
    ) -> dict[str, object] | None:
        """Create the recommended follow-up after a cancellation."""
        order_number = str(result.get("order_number") or payload.get("order_number") or "").strip()
        if not order_number:
            return None

        payment_followup_task_id = str(result.get("payment_followup_task_id") or "").strip()
        finance_fragment = (
            f" Además quedó creada la tarea {payment_followup_task_id} para revisar el"
            " reembolso o la devolución."
            if payment_followup_task_id
            else ""
        )
        return {
            "kind": "customer_message",
            "title": "Confirmar cancelación al cliente",
            "summary": (
                f"La cancelación del pedido {order_number} ya se ejecutó. Conviene notificar al"
                f" cliente y explicarle el siguiente paso financiero si aplica.{finance_fragment}"
            ),
            "suggested_message": (
                f"Hola, confirmamos la cancelación del pedido {order_number} según tu solicitud."
                " Si hubo un pago aprobado, nuestro equipo va a revisar el siguiente paso"
                " administrativo y te vamos a mantener al tanto."
            ),
            "suggested_prompt": (
                f"Mandale un WhatsApp al cliente del pedido {order_number} confirmando la"
                " cancelación y aclarando que, si hubo un pago aprobado, vamos a revisar el"
                " siguiente paso administrativo."
            ),
        }

    def _build_reservation_suggestion(
        self,
        *,
        payload: dict[str, object],
        result: dict[str, object],
    ) -> dict[str, object] | None:
        """Create the recommended follow-up after a stock reservation."""
        quantity = result.get("quantity") or payload.get("quantity")
        sku = str(result.get("sku") or payload.get("sku") or "").strip()
        wine_name = str(result.get("wine_name") or "").strip()
        order_number = str(result.get("order_number") or payload.get("order_number") or "").strip()
        remaining_stock = result.get("remaining_stock")
        if not sku or quantity in (None, ""):
            return None

        wine_reference = wine_name or sku
        order_fragment = f" para el pedido {order_number}" if order_number else ""
        remaining_fragment = (
            f" Quedaron {remaining_stock} unidades disponibles."
            if remaining_stock is not None
            else ""
        )
        return {
            "kind": "internal_follow_up",
            "title": "Confirmar reserva operativa",
            "summary": (
                f"La reserva de {quantity} unidad(es) de {wine_reference}{order_fragment} ya está"
                f" activa.{remaining_fragment}"
            ),
            "suggested_message": (
                f"Reserva activa: {quantity} unidad(es) de {wine_reference}{order_fragment}."
                f"{remaining_fragment}"
            ),
            "suggested_prompt": (
                f"Creá una nota interna confirmando que quedaron reservadas {quantity} unidad(es)"
                f" de {wine_reference}{order_fragment}.{remaining_fragment}"
            ),
        }

    def _resolve_conversation(self, action_payload: dict[str, object]) -> Conversation | None:
        """Resolve the original conversation when available."""
        conversation_id = str(action_payload.get("conversation_id") or "").strip()
        if not conversation_id:
            return None
        return Conversation.objects.filter(id=conversation_id).first()
