"""API client errors."""

from __future__ import annotations


class ApiError(RuntimeError):
    """A Systems Modeling API request failed."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status
        self.detail = detail
