from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    app_name: str = "ServiceAI Backend"
    debug: bool = False

    database_url: str = Field(
        ..., description="SQLAlchemy async URL, e.g. postgresql+asyncpg://user:pass@localhost:5432/db",
    )

    jwt_secret_key: str = Field(..., min_length=32)
    jwt_refresh_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 15
    refresh_token_expires_days: int = 30


settings = Settings()
