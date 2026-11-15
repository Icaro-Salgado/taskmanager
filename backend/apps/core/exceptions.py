"""Domain exceptions raised by services, policies and selectors.

They know nothing about HTTP; `apps.core.exception_handler` maps them to responses.
"""


class DomainError(Exception):
    default_code = "domain_error"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code


class NotFoundError(DomainError):
    """The resource does not exist, or the user may not know it exists."""

    default_code = "not_found"


class PermissionDeniedError(DomainError):
    """The user can see the resource but may not perform this action on it."""

    default_code = "permission_denied"


class RuleViolationError(DomainError):
    """The action breaks a business rule (for example, editing a finished task)."""

    default_code = "rule_violation"


class ConflictError(DomainError):
    """The action conflicts with the current state (for example, an existing membership)."""

    default_code = "conflict"
