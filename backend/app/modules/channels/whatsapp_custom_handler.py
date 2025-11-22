"""Custom WhatsApp handler stub."""

from app.modules.channels.schemas import ChannelType, NormalizedIncomingMessage


class WhatsAppCustomHandler:
    def __init__(self, channels_service, dialog_service):
        self._channels_service = channels_service
        self._dialog_service = dialog_service

    async def handle_webhook(self, bot_id: int, payload: dict, headers: dict | None = None) -> None:
        normalized = NormalizedIncomingMessage(
            bot_id=bot_id,
            channel_id=int(payload.get("channel_id", 0)),
            channel_type=ChannelType.WHATSAPP_CUSTOM,
            external_user_id=str(payload.get("user", "0")),
            external_message_id=str(payload.get("message_id")) if payload.get("message_id") else None,
            text=str(payload.get("text", "")),
            payload=payload,
        )
        await self._dialog_service.process_incoming_message(normalized)

    async def send_message(self, bot_id: int, external_chat_id: str, text: str, attachments=None) -> None:
        return None
