from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/postgres"

    backend_cors_origins: str = ""

    firebase_service_account_json_path: str | None = None
    firebase_service_account_json: str | None = None


settings = Settings()
