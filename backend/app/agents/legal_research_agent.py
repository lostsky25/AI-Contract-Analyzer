from app.config import settings

LEGAL_DISCLAIMER = (
    "Legal research uses public web pages only and does not access closed legal systems."
)


class LegalResearchAgent:
    def run(self, query: str) -> dict:
        # MVP-safe mode: preserve architecture contract and return transparent metadata.
        # External provider integration can be enabled later without changing API shape.
        if not settings.legal_web_search_enabled:
            return {
                "legal_sources": [],
                "warnings": ["Legal web search disabled by configuration."],
                "provider": settings.legal_search_provider,
                "allowed_domains": settings.legal_allowed_domains,
            }

        return {
            "legal_sources": [],
            "warnings": [
                "Public legal sources were not resolved in this run.",
                LEGAL_DISCLAIMER,
            ],
            "provider": settings.legal_search_provider,
            "allowed_domains": settings.legal_allowed_domains,
        }
