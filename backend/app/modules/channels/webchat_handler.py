"""Webchat handler stub using websocket manager."""

from datetime import datetime

from app.modules.channels.schemas import ChannelType, NormalizedMessage


class WebchatHandler:
    def __init__(self, dialog_service, websocket_manager):
        self._dialog_service = dialog_service
        self._ws = websocket_manager

    async def handle_user_message(self, bot_id: int, session_id: str, text: str) -> None:
        normalized = NormalizedMessage(
            bot_id=bot_id,
            channel_type=ChannelType.WEBCHAT,
            external_chat_id=session_id,
            external_user_id=session_id,
            text=text,
            attachments=[],
            timestamp=datetime.utcnow(),
            raw_update={"source": "webchat"},
        )
        await self._dialog_service.process_incoming_message(normalized)

    async def send_message_to_user(self, bot_id: int, session_id: str, text: str, attachments=None) -> None:
        message = {"type": "webchat_message", "bot_id": bot_id, "session_id": session_id, "text": text}
        await self._ws.send_to_webchat(bot_id, session_id, message)
