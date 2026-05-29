from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    upload_dir: str = "uploads"
    max_file_size_mb: int = 20
    allowed_extensions: list[str] = Field(default_factory=lambda: [".pdf", ".docx"])
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_ocr_model: str = "nvidia/nemotron-nano-12b-v2-vl"
    openrouter_model_risk: str = "nvidia/nemotron-3-super-120b-a12b:free"
    openrouter_model_key_terms: str = "google/gemma-4-31b-it:free"
    openrouter_model_qa: str = "nvidia/nemotron-3-super-120b-a12b:free"
    openrouter_model_legal_research: str = "openrouter/owl-alpha"
    openrouter_model_fallback: str = "deepseek/deepseek-v4-flash:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    chroma_db_dir: str = "./chroma_db"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    legal_web_search_enabled: bool = True
    legal_search_provider: str = "openrouter_web_search"
    legal_allowed_domains: str = "consultant.ru,garant.ru,pravo.gov.ru"
    legal_search_max_results: int = 3
    legal_search_context_size: str = "low"
    database_url: str = (
        "postgresql://postgres:postgres@localhost:5432/ai_contract_analyzer"
    )
    tesseract_cmd: str | None = None
    poppler_path: str | None = None
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
