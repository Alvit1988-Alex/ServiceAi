from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import AliasChoices, Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", BASE_DIR.parent / ".env"),
        case_sensitive=False,
    )

    app_name: str = "ServiceAI Backend"

    # Environment / Debug
    # Support both ENV and APP_ENV (plus 'env') to avoid breaking existing deployments.
    environment: Literal["development", "staging", "production", "test"] = Field(
        default="development",
        validation_alias=AliasChoices("ENV", "APP_ENV", "environment", "env"),
        description="Deployment environment used for safety checks.",
    )
    debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("DEBUG", "debug"),
        description="Enable debug features; must be false in production.",
    )

    # Database
    database_url: str = Field(
        ...,
        description="SQLAlchemy async URL, e.g. postgresql+asyncpg://user:pass@localhost:5432/db",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )
    db_auto_create: bool = Field(
        default=False,
        validation_alias=AliasChoices("DB_AUTO_CREATE", "db_auto_create"),
        description="When true, create_all can be used to bootstrap tables automatically (dev only).",
    )

    # JWT
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

    # Telegram auth
    auth_telegram_only: bool = Field(
        default=False,
        validation_alias=AliasChoices("AUTH_TELEGRAM_ONLY", "auth_telegram_only"),
        description="When true, disable password-based login and password changes",
    )
    telegram_auth_bot_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TELEGRAM_AUTH_BOT_TOKEN", "telegram_auth_bot_token"),
    )
    telegram_auth_bot_username: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TELEGRAM_AUTH_BOT_USERNAME", "telegram_auth_bot_username"),
    )
    telegram_webhook_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TELEGRAM_WEBHOOK_SECRET", "telegram_webhook_secret"),
    )
    telegram_webhook_path: str = Field(
        default="/auth/telegram/webhook",
        validation_alias=AliasChoices("TELEGRAM_WEBHOOK_PATH", "telegram_webhook_path"),
    )
    public_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PUBLIC_BASE_URL", "public_base_url"),
        description="Publicly accessible base URL used for building webhooks",
    )
    front_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("FRONT_BASE_URL", "front_base_url"),
        description="Publicly accessible frontend base URL used for building webchat embed links",
    )

    # Internal security
    channel_config_secret_key: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("CHANNEL_CONFIG_SECRET_KEY", "channel_config_secret_key"),
    )
    internal_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("INTERNAL_API_KEY", "internal_api_key"),
    )

    # GigaChat
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

    ai_llm_provider: str = Field(
        default="gigachat",
        validation_alias=AliasChoices("AI_LLM_PROVIDER", "ai_llm_provider"),
        description="LLM provider: gigachat|openai",
    )
    ai_embeddings_provider: str = Field(
        default="gigachat",
        validation_alias=AliasChoices("AI_EMBEDDINGS_PROVIDER", "ai_embeddings_provider"),
        description="Embeddings provider: gigachat|openai",
    )
    openai_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_BASE_URL", "openai_base_url"),
        description="OpenAI-compatible base URL (e.g. http://127.0.0.1:12345/v1)",
    )
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"),
        description="OpenAI-compatible API key (LM Studio can be any non-empty string)",
    )
    openai_chat_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_CHAT_MODEL", "openai_chat_model"),
        description="Chat model id for OpenAI-compatible providers",
    )
    openai_embedding_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_EMBEDDING_MODEL", "openai_embedding_model"),
        description="Embeddings model id for OpenAI-compatible providers",
    )
    strip_think_tags: bool = Field(
        default=True,
        validation_alias=AliasChoices("STRIP_THINK_TAGS", "strip_think_tags"),
        description="When true, removes <think>...</think> blocks from model responses.",
    )

    # CORS
    cors_allow_origins: list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("CORS_ALLOW_ORIGINS", "cors_allow_origins"),
        description="Comma-separated list of allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(
        default=True,
        validation_alias=AliasChoices("CORS_ALLOW_CREDENTIALS", "cors_allow_credentials"),
    )
    cors_allow_methods: list[str] = Field(
        default=["*"],
        validation_alias=AliasChoices("CORS_ALLOW_METHODS", "cors_allow_methods"),
        description="Comma-separated list of allowed HTTP methods",
    )
    cors_allow_headers: list[str] = Field(
        default=["*"],
        validation_alias=AliasChoices("CORS_ALLOW_HEADERS", "cors_allow_headers"),
        description="Comma-separated list of allowed HTTP headers",
    )

    webchat_static_dir: str = Field(
        default=str((BASE_DIR / "../frontend/public/static").resolve()),
        validation_alias=AliasChoices("WEBCHAT_STATIC_DIR", "webchat_static_dir"),
        description="Filesystem path to frontend public/static for webchat assets",
    )

    # Bitrix24 OAuth
    bitrix24_app_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BITRIX24_APP_CLIENT_ID", "bitrix24_app_client_id"),
    )
    bitrix24_app_client_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BITRIX24_APP_CLIENT_SECRET", "bitrix24_app_client_secret"),
    )
    bitrix24_app_redirect_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BITRIX24_APP_REDIRECT_URL", "bitrix24_app_redirect_url"),
    )
    bitrix24_app_scopes: str = Field(
        default="imopenlines,im,crm",
        validation_alias=AliasChoices("BITRIX24_APP_SCOPES", "bitrix24_app_scopes"),
    )
    bitrix24_oauth_token_url: str | None = Field(
        default="https://oauth.bitrix.info/oauth/token/",
        validation_alias=AliasChoices("BITRIX24_OAUTH_TOKEN_URL", "bitrix24_oauth_token_url"),
    )
    bitrix24_app_application_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BITRIX24_APP_APPLICATION_TOKEN", "bitrix24_app_application_token"),
    )
    bitrix24_connect_state_secret: str = Field(
        default="",
        validation_alias=AliasChoices("BITRIX24_CONNECT_STATE_SECRET", "bitrix24_connect_state_secret"),
    )

    # ---------- helpers ----------
    @classmethod
    def _parse_csv_list(cls, value: Any) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, str):
            raw_items = value.split(",")
        else:
            raw_items = value
        items = [str(item).strip() for item in raw_items]
        filtered_items = [item for item in items if item]
        return filtered_items

    # ---------- validators ----------
    @field_validator("environment", mode="before")
    @classmethod
    def _normalize_environment(cls, value: str | None) -> str:
        if value is None:
            return "development"
        normalized = str(value).strip().lower()
        allowed = {"development", "staging", "production", "test"}
        if normalized not in allowed:
            raise ValueError("ENV/APP_ENV must be one of: development, staging, production, test")
        return normalized

    @field_validator("debug")
    @classmethod
    def _guard_debug_in_production(cls, value: bool, info: ValidationInfo) -> bool:
        env = (info.data.get("environment") or "development").lower()
        if env == "production" and value:
            raise ValueError("DEBUG cannot be enabled when ENV/APP_ENV=production")
        return value

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _normalize_cors_allow_origins(cls, value: Any) -> list[str] | None:
        return cls._parse_csv_list(value)

    @field_validator("cors_allow_methods", mode="before")
    @classmethod
    def _normalize_cors_allow_methods(cls, value: Any) -> list[str]:
        parsed = cls._parse_csv_list(value)
        return parsed if parsed is not None else value

    @field_validator("cors_allow_headers", mode="before")
    @classmethod
    def _normalize_cors_allow_headers(cls, value: Any) -> list[str]:
        parsed = cls._parse_csv_list(value)
        return parsed if parsed is not None else value

    @field_validator("webchat_static_dir", mode="before")
    @classmethod
    def _normalize_webchat_static_dir(cls, value: str | None) -> str:
        if value is None:
            return str((BASE_DIR / "../frontend/public/static").resolve())
        return str(Path(value).expanduser().resolve())

    @field_validator("db_auto_create")
    @classmethod
    def _guard_db_auto_create(cls, value: bool, info: ValidationInfo) -> bool:
        env = (info.data.get("environment") or "development").lower()
        debug = bool(info.data.get("debug"))

        # Allow DB auto-create ONLY for local dev bootstrap:
        # - debug must be true
        # - environment must NOT be production
        if value and (env == "production" or not debug):
            raise ValueError(
                "DB_AUTO_CREATE is disabled when DEBUG=false or ENV/APP_ENV=production. НЕ ИСПОЛЬЗОВАТЬ В PRODUCTION."
            )
        return value

    # ---------- convenience ----------
    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def runtime_debug(self) -> bool:
        return self.debug and self.is_development


settings = Settings()
