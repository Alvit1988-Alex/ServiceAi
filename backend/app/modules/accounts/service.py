"""Service layer for account operations."""

from app.modules.accounts.models import Account


class AccountsService:
    async def list_accounts(self) -> list[Account]:
        return []
