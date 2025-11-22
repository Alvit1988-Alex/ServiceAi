"""WhatsApp Green API handler stub."""

from app.modules.channels.schemas import ChannelType, NormalizedIncomingMessage


class WhatsAppGreenHandler:
    def __init__(self, channels_service, dialog_service):
        self._channels_service = channels_service
        self._dialog_service = dialog_service

    async def handle_notification(self, bot_id: int, notification: dict) -> None:
        normalized = NormalizedIncomingMessage(
            bot_id=bot_id,
            channel_id=int(notification.get("channel_id", 0)),
            channel_type=ChannelType.WHATSAPP_GREEN,
            external_user_id=str(notification.get("user", "0")),
            external_message_id=str(notification.get("message_id"))
            if notification.get("message_id")
            else None,
            text=str(notification.get("text", "")),
            payload=notification,
        )
        await self._dialog_service.process_incoming_message(normalized)

    async def send_message(self, bot_id: int, external_chat_id: str, text: str, attachments=None) -> None:
        return None
