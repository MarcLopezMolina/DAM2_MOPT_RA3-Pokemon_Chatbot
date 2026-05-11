from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    ok: bool
    tool: str
    content: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    intent: str | None = None
    step: str | None = None
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    next_action: str | None = None
