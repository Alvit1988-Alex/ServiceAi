"""Dialog service placeholder implementing minimal flow."""

from datetime import datetime

from app.modules.channels.schemas import NormalizedMessage
from app.modules.dialogs.schemas import DialogStatus


class Dialog:
    """In-memory dialog stub."""

    def __init__(self, bot_id: int, external_channel: str, external_chat_id: str, external_user_id: str):
        self.id = 0
        self.bot_id = bot_id
        self.external_channel = external_channel
        self.external_chat_id = external_chat_id
        self.external_user_id = external_user_id
        self.status = DialogStatus.AUTO
        self.last_message_at = datetime.utcnow()


class DialogService:
    def __init__(self, ai_service, channel_sender_registry):
        self._ai_service = ai_service
        self._channel_sender_registry = channel_sender_registry

    async def process_incoming_message(self, msg: NormalizedMessage) -> None:
        # Placeholder: echo behaviour only.
        dialog = Dialog(
            bot_id=msg.bot_id,
            external_channel=msg.channel_type,
            external_chat_id=msg.external_chat_id,
            external_user_id=msg.external_user_id,
        )
        dialog.last_message_at = datetime.utcnow()
        await self._reply_auto(dialog, msg)

    async def _reply_auto(self, dialog: Dialog, msg: NormalizedMessage) -> None:
        sender = self._channel_sender_registry.get_sender(msg.channel_type) if self._channel_sender_registry._map else None
        if sender:
            await sender.send_message(dialog.bot_id, dialog.external_chat_id, msg.text or "")
