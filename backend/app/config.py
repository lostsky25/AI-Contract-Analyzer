from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    upload_dir: str = "uploads"
    max_file_size_mb: int = 20
    allowed_extensions: list[str] = Field(default_factory=lambda: [".pdf", ".docx"])
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_ocr_model: str = "nvidia/nemotron-nano-12b-v2-vl"
    openrouter_base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    chroma_db_dir: str = "./chroma_db"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
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
