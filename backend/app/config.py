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
    chroma_db_dir: str = "./chroma_db"
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        validation_alias=AliasChoices("EMBEDDING_MODEL_NAME", "EMBEDDING_MODEL"),
    )
    legal_web_search_enabled: bool = True
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
    ocr_vlm_max_pages: int = 20
    ocr_vlm_dpi: int = 160
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


settings = Settings()
