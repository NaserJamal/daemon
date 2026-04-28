"""
Safety module for nanocode.

Provides danger detection and user confirmation for potentially
harmful operations, especially bash commands.
"""

from nanocode.safety.danger import DangerDetector, danger_reason
from nanocode.safety.confirm import confirm, ConfirmPrompt

__all__ = [
    "DangerDetector",
    "danger_reason",
    "confirm",
    "ConfirmPrompt",
]
