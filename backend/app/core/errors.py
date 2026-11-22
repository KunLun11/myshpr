"""Domain errors and RFC 7807-ish problem responses."""

from typing import Any


class AppError(Exception):
    """Application-level error carrying a machine-readable ``code``."""

    def __init__(
        self,
        code: str,
        detail: str,
        *,
        status_code: int = 400,
        errors: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status_code = status_code
        self.errors = errors or []
        self.headers = headers or {}

    def to_problem(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "type": "about:blank",
            "title": self.code,
            "status": self.status_code,
            "detail": self.detail,
            "code": self.code,
        }
        if self.errors:
            body["errors"] = self.errors
        return body


class NotFoundError(AppError):
    def __init__(self, detail: str = "Resource not found", code: str = "NOT_FOUND") -> None:
        super().__init__(code, detail, status_code=404)


class ForbiddenError(AppError):
    def __init__(self, detail: str = "Access denied", code: str = "FORBIDDEN") -> None:
        super().__init__(code, detail, status_code=403)


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "Authentication required", code: str = "UNAUTHORIZED") -> None:
        super().__init__(code, detail, status_code=401)


class ConflictError(AppError):
    def __init__(self, detail: str, code: str = "CONFLICT") -> None:
        super().__init__(code, detail, status_code=409)


class ValidationError(AppError):
    def __init__(
        self,
        detail: str,
        code: str = "VALIDATION_ERROR",
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(code, detail, status_code=422, errors=errors)
