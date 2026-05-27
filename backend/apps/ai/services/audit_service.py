"""Audit helpers for AI runs."""

from __future__ import annotations

from django.utils import timezone

from apps.ai.models import AgentRun, ToolExecution


class AuditService:
    """Persist tool execution audit records."""

    def log_tool_execution(
        self,
        *,
        run: AgentRun,
        tool_name: str,
        risk_level: str,
        input_payload: dict[str, object],
        output_payload: dict[str, object],
        latency_ms: int,
        status: str = ToolExecution.Status.SUCCEEDED,
        error: str = "",
    ) -> ToolExecution:
        """Create a tool execution record."""
        execution = ToolExecution.objects.create(
            run=run,
            tool_name=tool_name,
            risk_level=risk_level,
            status=status,
            input_payload=input_payload,
            output_payload=output_payload,
            latency_ms=latency_ms,
            error=error,
        )
        run.updated_at = timezone.now()
        run.save(update_fields=["updated_at"])
        return execution
