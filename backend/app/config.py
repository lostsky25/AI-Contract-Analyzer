from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    upload_dir: str = "uploads"
    max_file_size_mb: int = 20
    allowed_extensions: list[str] = Field(default_factory=lambda: [".pdf", ".docx"])
    openrouter_api_key: str = ""
    openrouter_model: str = ""
    chroma_db_dir: str = "./chroma_db"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    database_url: str = (
        "postgresql://postgres:postgres@localhost:5432/ai_contract_analyzer"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
