"""Custom WhatsApp handler stub."""

from datetime import datetime

from app.modules.channels.schemas import ChannelType, NormalizedMessage


class WhatsAppCustomHandler:
    def __init__(self, channels_service, dialog_service):
        self._channels_service = channels_service
        self._dialog_service = dialog_service

    async def handle_webhook(self, bot_id: int, payload: dict, headers: dict | None = None) -> None:
        normalized = NormalizedMessage(
            bot_id=bot_id,
            channel_type=ChannelType.WHATSAPP_CUSTOM,
            external_chat_id=str(payload.get("chat", "0")),
            external_user_id=str(payload.get("user", "0")),
            text=str(payload.get("text", "")),
            attachments=[],
            timestamp=datetime.utcnow(),
            raw_update=payload,
        )
        await self._dialog_service.process_incoming_message(normalized)

    async def send_message(self, bot_id: int, external_chat_id: str, text: str, attachments=None) -> None:
        return None
