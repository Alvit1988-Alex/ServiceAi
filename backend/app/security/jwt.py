"""JWT placeholder implementation."""

from typing import Any


def verify_token(token: str) -> dict[str, Any]:
    # In a real app, validate JWT signature and expiry.
    return {"token": token}
