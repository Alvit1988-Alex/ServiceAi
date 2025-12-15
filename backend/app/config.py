from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", BASE_DIR.parent / ".env"),
        case_sensitive=False,
    )

    app_name: str = "ServiceAI Backend"
    debug: bool = False

    database_url: str = Field(
        ...,
        description="SQLAlchemy async URL, e.g. postgresql+asyncpg://user:pass@localhost:5432/db",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )

    jwt_secret_key: str = Field(
        ...,
        min_length=32,
        validation_alias=AliasChoices("JWT_SECRET_KEY", "jwt_secret_key"),
    )
    jwt_refresh_secret_key: str = Field(
        ...,
        min_length=32,
        validation_alias=AliasChoices("JWT_REFRESH_SECRET_KEY", "jwt_refresh_secret_key"),
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias=AliasChoices("JWT_ALGORITHM", "jwt_algorithm"))
    access_token_expires_minutes: int = Field(
        default=15,
        validation_alias=AliasChoices("ACCESS_TOKEN_EXPIRES_MINUTES", "access_token_expires_minutes"),
    )
    refresh_token_expires_days: int = Field(
        default=30,
        validation_alias=AliasChoices("REFRESH_TOKEN_EXPIRES_DAYS", "refresh_token_expires_days"),
    )

    public_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PUBLIC_BASE_URL", "public_base_url"),
        description="Publicly accessible base URL used for building webhooks",
    )

    channel_config_secret_key: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("CHANNEL_CONFIG_SECRET_KEY", "channel_config_secret_key"),
    )

    internal_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("INTERNAL_API_KEY", "internal_api_key"),
    )

    gigachat_client_id: str | None = Field(default=None, validation_alias=AliasChoices("GIGACHAT_CLIENT_ID", "gigachat_client_id"))
    gigachat_client_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GIGACHAT_CLIENT_SECRET", "gigachat_client_secret"),
    )
    gigachat_auth_url: str | None = Field(default=None, validation_alias=AliasChoices("GIGACHAT_AUTH_URL", "gigachat_auth_url"))
    gigachat_api_url: str | None = Field(default=None, validation_alias=AliasChoices("GIGACHAT_API_URL", "gigachat_api_url"))
    gigachat_scope: str | None = Field(default=None, validation_alias=AliasChoices("GIGACHAT_SCOPE", "gigachat_scope"))
    gigachat_use_tls_cert: bool = Field(
        default=False,
        validation_alias=AliasChoices("GIGACHAT_USE_TLS_CERT", "gigachat_use_tls_cert"),
    )
    gigachat_cert_path: str | None = Field(default=None, validation_alias=AliasChoices("GIGACHAT_CERT_PATH", "gigachat_cert_path"))


settings = Settings()
