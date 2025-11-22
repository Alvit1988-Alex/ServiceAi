"""Bots service stub."""

from app.modules.bots.models import Bot
from app.modules.bots.schemas import BotCreateIn


class BotsService:
    async def list_bots(self) -> list[Bot]:
        return []

    async def create_bot(self, data: BotCreateIn) -> Bot:
        bot = Bot(id=0, account_id=0, name=data.name, description=data.description)
        return bot
