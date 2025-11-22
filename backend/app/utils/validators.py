"""Validation helpers."""


def validate_pagination(page: int, per_page: int) -> None:
    if page < 1:
        raise ValueError("page must be >= 1")
    if per_page < 1 or per_page > 100:
        raise ValueError("per_page must be between 1 and 100")
