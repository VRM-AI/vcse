"""API error models."""

from __future__ import annotations

# --- Operational error codes ---
API_INVALID_REQUEST = "API_INVALID_REQUEST"
API_NOT_FOUND = "API_NOT_FOUND"
API_RUNTIME_INVALID = "API_RUNTIME_INVALID"
API_PROOF_INVALID = "API_PROOF_INVALID"
API_BUNDLE_INVALID = "API_BUNDLE_INVALID"
API_UNSUPPORTED_OPERATION = "API_UNSUPPORTED_OPERATION"
API_INTERNAL_ERROR = "API_INTERNAL_ERROR"


class APIError(ValueError):
    def __init__(
        self,
        error_type: str,
        message: str,
        code: str,
        status_code: int = 400,
    ) -> None:
        super().__init__(f"{error_type}: {message}")
        self.error_type = error_type
        self.message = message
        self.code = code
        self.status_code = status_code


class OperationalError(Exception):
    """Raised by operational route handlers for structured error responses."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        path: str = "",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.path = path


def error_payload(error_type: str, message: str, code: str) -> dict[str, dict[str, str]]:
    return {
        "error": {
            "type": error_type,
            "message": message,
            "code": code,
        }
    }
