"""Central tool registry."""

from __future__ import annotations

from time import perf_counter

from apps.ai.models import ToolExecution
from apps.ai.services.audit_service import AuditService

from .base import ToolContext, ToolSpec
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
                    handler=get_order_by_number,
                ),
                ToolSpec(
                    name="search_catalog",
                    description="Search the wine catalog.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    handler=search_catalog,
                ),
                ToolSpec(
                    name="get_stock_snapshot",
                    description="Get current stock for one wine.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    handler=get_stock_snapshot,
                ),
                ToolSpec(
                    name="search_knowledge_base",
                    description="Search the AI knowledge base.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    handler=search_knowledge_base,
                ),
                ToolSpec(
                    name="list_low_stock_items",
                    description="List wines with low stock.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    handler=list_low_stock_items,
                ),
                ToolSpec(
                    name="list_pending_orders",
                    description="List pending operational orders.",
                    risk_level=ToolExecution.RiskLevel.READ_ONLY,
                    handler=list_pending_orders,
                ),
            ]
        }
        self._audit_service = AuditService()

    def execute(
        self,
        *,
        tool_name: str,
        payload: dict[str, object],
        context: ToolContext,
    ) -> dict[str, object]:
        """Execute a registered tool and audit the result."""
        spec = self._tools[tool_name]
        started_at = perf_counter()
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
