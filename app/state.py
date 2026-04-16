from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppState:
    waiting_room: list[dict[str, Any]] = field(default_factory=list)
    rooms: dict[str, dict[str, Any] | None] = field(
        default_factory=lambda: {
            "ED-1": None,
            "ED-2": None,
            "ED-3": None,
            "ED-4": None,
            "ED-5": None,
        }
    )


state = AppState()
