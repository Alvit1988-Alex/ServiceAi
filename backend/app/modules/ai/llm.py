"""LLM client stub."""


class LLMClient:
    async def generate(self, system_prompt: str, history: list[dict[str, str]], question: str, context_chunks: list[str]) -> str:
        return ""
