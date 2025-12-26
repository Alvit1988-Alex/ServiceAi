"""Tests for pending login status enum casing."""
from __future__ import annotations

from app.modules.auth.models import PendingLogin, PendingLoginStatus


def test_pending_login_status_values_are_lowercase() -> None:
    values = [status.value for status in PendingLoginStatus]
    assert values == ["pending", "confirmed", "expired"]


def test_pending_login_status_enum_column_uses_lowercase_values() -> None:
    enum_values = PendingLogin.__table__.c.status.type.enums
    assert enum_values == ["pending", "confirmed", "expired"]
