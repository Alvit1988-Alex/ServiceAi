"""Dialogs API router stub."""

from fastapi import APIRouter

from app.modules.dialogs.schemas import DialogOut

router = APIRouter(prefix="/bots/{bot_id}/dialogs", tags=["dialogs"])


@router.get("", response_model=list[DialogOut])
async def list_dialogs(bot_id: int) -> list[DialogOut]:
    return []
