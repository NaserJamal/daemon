"""Safety: danger detection and user confirmation."""

from daemon.safety.confirm import confirm
from daemon.safety.danger import DANGER_PATTERNS, danger_reason

__all__ = ["DANGER_PATTERNS", "confirm", "danger_reason"]
