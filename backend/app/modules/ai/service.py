"""AI service stub integrating instructions, RAG and LLM."""

from app.modules.ai.instructions_service import AIInstructionsService
from app.modules.ai.llm import LLMClient
from app.modules.ai.rag import RAGService
from app.modules.ai.schemas import AIAnswer


class AIService:
    def __init__(self, instructions_service: AIInstructionsService | None = None, rag_service: RAGService | None = None, llm_client: LLMClient | None = None):
        self._instructions_service = instructions_service or AIInstructionsService()
        self._rag_service = rag_service or RAGService()
        self._llm_client = llm_client or LLMClient()

    async def generate_answer(self, bot_id: int, dialog_id: int, user_message: str, hint_mode: bool = False) -> AIAnswer:
        return AIAnswer(can_answer=False, answer_text=None, confidence=0.0, used_chunk_ids=[])
