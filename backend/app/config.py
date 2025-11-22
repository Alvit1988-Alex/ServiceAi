from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", env_file_encoding="utf-8")

    app_name: str = "ServiceAI"
    debug: bool = True
    database_url: str = "sqlite+aiosqlite:///./local.db"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60


settings = Settings()
