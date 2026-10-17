"""Exception hierarchy for the ai-product-team controller.

Every error carries a short machine-readable ``code`` and a ``details`` mapping. The CLI maps these to
exit code 1 and a JSON error object. Runtime validation never uses bare ``assert``.
"""

from __future__ import annotations

from typing import Any


class AiptError(Exception):
    """Base class for all controller errors."""

    code: str = "error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serialisable error object used by the CLI."""
        return {"code": self.code, "message": self.message, "details": self.details}


class ValidationError(AiptError):
    """Schema or reference validation failed. ``errors`` lists JSON-pointer paths with messages."""

    code = "validation"

    def __init__(self, message: str, *, errors: list[str] | None = None, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details=details)
        self.errors: list[str] = list(errors or [])
        self.details.setdefault("errors", self.errors)


class NotFoundError(AiptError):
    """A referenced record, file or id does not exist."""

    code = "not_found"


class ConflictError(AiptError):
    """Stale expected state version, or an idempotency key reused with a different payload."""

    code = "conflict"


class TransitionError(AiptError):
    """An illegal run or task state change was requested."""

    code = "transition"


class PolicyError(AiptError):
    """Authority, independence, version-binding, write-scope or protected-scope violation."""

    code = "policy"


class BudgetExhausted(AiptError):
    """Admission refused because a task, concurrency, round or wall-clock limit is reached."""

    code = "budget"

    def __init__(self, message: str, *, partial_state: dict[str, Any] | None = None, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details=details)
        self.partial_state: dict[str, Any] = dict(partial_state or {})
        self.details.setdefault("partial_state", self.partial_state)


class ExecutionError(AiptError):
    """A command could not be started. A nonzero exit status is a recorded result, not this error."""

    code = "execution"
