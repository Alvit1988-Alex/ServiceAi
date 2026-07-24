import pytest
from fastapi import HTTPException

from app.modules.channels.router import _validate_max_secret


def test_validate_max_secret_accepts_valid_header():
    _validate_max_secret("webhook-secret", "webhook-secret")


@pytest.mark.parametrize("provided", [None, "wrong-secret"])
def test_validate_max_secret_rejects_missing_or_invalid_header(provided):
    with pytest.raises(HTTPException) as exc_info:
        _validate_max_secret("webhook-secret", provided)
    assert exc_info.value.status_code == 403


def test_validate_max_secret_rejects_missing_expected_secret():
    with pytest.raises(HTTPException) as exc_info:
        _validate_max_secret(None, "webhook-secret")
    assert exc_info.value.status_code == 403


def test_validate_max_secret_does_not_accept_access_token_as_secret():
    with pytest.raises(HTTPException):
        _validate_max_secret("webhook-secret", "access-token")
