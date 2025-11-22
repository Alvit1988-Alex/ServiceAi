"""Avito handler stub."""

from app.modules.channels.schemas import ChannelType, NormalizedIncomingMessage


class AvitoHandler:
    def __init__(self, channels_service, dialog_service):
        self._channels_service = channels_service
        self._dialog_service = dialog_service

    async def handle_update(self, bot_id: int, update: dict) -> None:
        normalized = NormalizedIncomingMessage(
            bot_id=bot_id,
            channel_id=int(update.get("channel_id", 0)),
            channel_type=ChannelType.AVITO,
            external_user_id=str(update.get("user", "0")),
            external_message_id=str(update.get("message_id")) if update.get("message_id") else None,
            text=str(update.get("text", "")),
            payload=update,
        )
        await self._dialog_service.process_incoming_message(normalized)

    async def send_message(self, bot_id: int, external_chat_id: str, text: str, attachments=None) -> None:
        return None
