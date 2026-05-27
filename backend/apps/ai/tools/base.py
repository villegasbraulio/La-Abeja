"""Base types for AI tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from apps.ai.models import AgentRun


@dataclass(slots=True)
class ToolContext:
    """Execution context passed to tools."""

    run: AgentRun
    user_id: str | None
    is_staff: bool


class ToolCallable(Protocol):
    """Callable tool contract."""

    def __call__(self, payload: dict[str, object], context: ToolContext) -> dict[str, object]:
        """Execute the tool and return structured JSON-friendly data."""


@dataclass(slots=True)
class ToolSpec:
    """Metadata describing a callable tool."""

    name: str
    description: str
    risk_level: str
    handler: ToolCallable
