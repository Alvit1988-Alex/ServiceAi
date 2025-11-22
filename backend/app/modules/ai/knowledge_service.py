"""Knowledge base service stub."""

from app.modules.ai.models import KnowledgeFile


class KnowledgeService:
    async def upload_file(self, bot_id: int, file) -> KnowledgeFile:
        return KnowledgeFile(id=0, bot_id=bot_id, file_name="placeholder", original_name="placeholder", size_bytes=0, chunks_count=0)

    async def list_files(self, bot_id: int) -> list[KnowledgeFile]:
        return []

    async def delete_file(self, bot_id: int, file_id: int) -> None:
        return None
