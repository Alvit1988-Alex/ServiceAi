"""WhatsApp Green API handler stub."""

from datetime import datetime

from app.modules.channels.schemas import ChannelType, NormalizedMessage


class WhatsAppGreenHandler:
    def __init__(self, channels_service, dialog_service):
        self._channels_service = channels_service
        self._dialog_service = dialog_service

    async def handle_notification(self, bot_id: int, notification: dict) -> None:
        normalized = NormalizedMessage(
            bot_id=bot_id,
            channel_type=ChannelType.WHATSAPP_GREEN,
            external_chat_id=str(notification.get("chat", "0")),
            external_user_id=str(notification.get("user", "0")),
            text=str(notification.get("text", "")),
            attachments=[],
            timestamp=datetime.utcnow(),
            raw_update=notification,
        )
        await self._dialog_service.process_incoming_message(normalized)

    async def send_message(self, bot_id: int, external_chat_id: str, text: str, attachments=None) -> None:
        return None
