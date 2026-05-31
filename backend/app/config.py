from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ENV_FILE = BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    env: str = Field(
        default="development",
        validation_alias=AliasChoices("ENV", "APP_ENV", "ENVIRONMENT"),
    )
    upload_dir: str = "uploads"
    max_file_size_mb: int = 20
    allowed_extensions: list[str] = Field(default_factory=lambda: [".pdf", ".docx"])
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_ocr_model: str = "nvidia/nemotron-nano-12b-v2-vl"
    openrouter_model_ocr_vlm: str = ""
    openrouter_model_risk: str = "nvidia/nemotron-3-super-120b-a12b:free"
    openrouter_model_key_terms: str = "google/gemma-4-31b-it:free"
    openrouter_model_qa: str = "nvidia/nemotron-3-super-120b-a12b:free"
    openrouter_model_legal_research: str = "openrouter/owl-alpha"
    openrouter_model_fallback: str = "deepseek/deepseek-v4-flash:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    llm_provider: str = "bothub"
    bothub_api_key: str = ""
    bothub_api_base_url: str = "https://openai.bothub.chat/v1"
    llm_api_base_url: str = ""
    llm_api_key: str = ""
    llm_model_risk: str = ""
    llm_model_key_terms: str = ""
    llm_model_qa: str = ""
    llm_model_fallback: str = ""
    llm_temperature: float = 0.2
    llm_include_usage: bool = False
    llm_timeout_seconds: int = 60
    vision_provider: str = "bothub"
    vision_api_base_url: str = ""
    vision_api_key: str = ""
    vision_model_ocr: str = ""
    vision_timeout_seconds: int = 120
    vision_include_usage: bool = False
    chroma_db_dir: str = "./chroma_db"
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        validation_alias=AliasChoices("EMBEDDING_MODEL_NAME", "EMBEDDING_MODEL"),
    )
    legal_web_search_enabled: bool = True
    legal_research_provider: str = "bothub_sonar"
    legal_research_model: str = ""
    legal_research_allowed_domains: str = "consultant.ru,garant.ru,pravo.gov.ru"
    legal_research_allow_model_reported_sources: bool = True
    legal_research_debug: bool = False
    legal_search_provider: str = "openrouter_web_search"
    legal_allowed_domains: str = "consultant.ru,garant.ru,pravo.gov.ru"
    legal_search_max_results: int = 3
    legal_search_context_size: str = "low"
    database_url: str = (
        "postgresql://postgres:postgres@localhost:5432/ai_contract_analyzer"
    )
    tesseract_cmd: str | None = None
    ocr_tesseract_lang: str = "rus+eng"
    poppler_path: str | None = None
    ocr_provider: str = "hybrid"
    ocr_use_vlm: bool = True
    ocr_debug: bool = False
    ocr_vlm_max_pages: int = 20
    ocr_vlm_dpi: int = 220
    ocr_vlm_timeout_seconds: int = 120
    ocr_min_text_chars_per_page: int = 50
    jwt_secret_key: str = "demo-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ENV_FILE) if BACKEND_ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @model_validator(mode="after")
    def validate_jwt_secret_policy(self) -> "Settings":
        if self.env.strip().lower() != "production":
            return self

        secret = self.jwt_secret_key.strip()
        weak_defaults = {"", "change-me-in-production", "demo-only-change-me"}
        if secret in weak_defaults:
            raise ValueError(
                "JWT_SECRET_KEY must be explicitly set to a strong value when ENV=production."
            )
        return self

    def get_text_llm_provider(self) -> str:
        provider = self.llm_provider.strip().lower()
        if provider in {"openrouter", "bothub"}:
            return provider
        return "openrouter"

    def get_text_llm_model(self, model_kind: str) -> str:
        provider = self.get_text_llm_provider()
        model_attr = {
            "risk": "llm_model_risk",
            "key_terms": "llm_model_key_terms",
            "qa": "llm_model_qa",
            "fallback": "llm_model_fallback",
        }.get(model_kind, "")

        if provider == "bothub":
            model = str(getattr(self, model_attr, "") or "").strip()
            return model

        legacy_attr = {
            "risk": "openrouter_model_risk",
            "key_terms": "openrouter_model_key_terms",
            "qa": "openrouter_model_qa",
            "fallback": "openrouter_model_fallback",
        }.get(model_kind, "")
        return str(getattr(self, legacy_attr, "") or "").strip()

    def get_vision_provider(self) -> str:
        provider = self.vision_provider.strip().lower()
        if provider in {"openrouter", "bothub", "disabled"}:
            return provider
        return "openrouter"

    def _get_openrouter_base_url(self) -> str:
        endpoint = str(self.openrouter_base_url or "").strip()
        if endpoint.endswith("/chat/completions"):
            return endpoint[: -len("/chat/completions")]
        return endpoint

    def get_text_llm_api_key(self) -> str:
        provider = self.get_text_llm_provider()
        if provider == "bothub":
            return str(self.bothub_api_key or "").strip()
        return str(self.openrouter_api_key or "").strip()

    def get_text_llm_base_url(self) -> str:
        provider = self.get_text_llm_provider()
        if provider == "bothub":
            return str(self.bothub_api_base_url or "").strip()
        return self._get_openrouter_base_url()

    def get_vision_api_key(self) -> str:
        provider = self.get_vision_provider()
        if provider == "bothub":
            return str(self.bothub_api_key or "").strip()
        if provider == "openrouter":
            return str(self.openrouter_api_key or "").strip()
        return ""

    def get_vision_base_url(self) -> str:
        provider = self.get_vision_provider()
        if provider == "bothub":
            return str(self.bothub_api_base_url or "").strip()
        if provider == "openrouter":
            return self._get_openrouter_base_url()
        return ""

    def get_legal_research_provider(self) -> str:
        provider = self.legal_research_provider.strip().lower()
        if provider in {
            "bothub_sonar",
            "bothub_web_search",
            "openrouter_web_search",
            "disabled",
        }:
            return provider
        return "bothub_sonar"

    def get_legal_research_api_key(self, provider: str | None = None) -> str:
        resolved = (provider or self.get_legal_research_provider()).strip().lower()
        if resolved in {"bothub_sonar", "bothub_web_search"}:
            return str(self.bothub_api_key or "").strip()
        if resolved == "openrouter_web_search":
            return str(self.openrouter_api_key or "").strip()
        return ""

    def get_legal_research_base_url(self, provider: str | None = None) -> str:
        resolved = (provider or self.get_legal_research_provider()).strip().lower()
        if resolved in {"bothub_sonar", "bothub_web_search"}:
            return str(self.bothub_api_base_url or "").strip()
        if resolved == "openrouter_web_search":
            return self._get_openrouter_base_url()
        return ""

    def get_legal_research_model(self, provider: str | None = None) -> str:
        resolved = (provider or self.get_legal_research_provider()).strip().lower()
        if resolved in {"bothub_sonar", "bothub_web_search"}:
            return str(self.legal_research_model or "").strip()
        if resolved == "openrouter_web_search":
            return str(self.openrouter_model_legal_research or "").strip()
        return ""


settings = Settings()
