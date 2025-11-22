"""Bots API router."""

from fastapi import APIRouter

from app.modules.bots.schemas import BotCreateIn, BotOut
from app.modules.bots.service import BotsService

router = APIRouter(prefix="/bots", tags=["bots"])


@router.get("", response_model=list[BotOut])
async def list_bots(service: BotsService = BotsService()) -> list[BotOut]:
    return await service.list_bots()


@router.post("", response_model=BotOut)
async def create_bot(data: BotCreateIn, service: BotsService = BotsService()) -> BotOut:
    return await service.create_bot(data=data)
