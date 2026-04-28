"""Safety: danger detection and user confirmation."""

from nanocode.safety.confirm import confirm
from nanocode.safety.danger import DANGER_PATTERNS, danger_reason

__all__ = ["DANGER_PATTERNS", "confirm", "danger_reason"]
