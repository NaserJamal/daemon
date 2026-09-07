"""Utils: small, cross-cutting helpers.

A module earns a place here only if it is used by more than one package and
carries no knowledge of any specific tool, command, or provider. Anything
that knows what it is being used for belongs in that domain instead.
"""

from daemon.utils.spill import spill

__all__ = ["spill"]
