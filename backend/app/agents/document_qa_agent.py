from app.config import settings
from app.services.llm_service import ask_llm_text

SYSTEM_PROMPT = (
    "You answer questions about a contract using provided context only. "
    "If context is insufficient, say that information is not available."
)


class DocumentQAAgent:
    def run(self, question: str, context: str) -> dict:
        answer = ask_llm_text(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"Question:\n{question}\n\nContext:\n{context}",
            model=settings.openrouter_model_qa,
        )
        return {
            "answer": answer,
            "model": settings.openrouter_model_qa,
            "fallback_model": settings.openrouter_model_fallback,
        }
