from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    log_level: str = "INFO"
    fx_base_url: str = "https://api.frankfurter.dev/v1"
    fx_timeout_seconds: float = 5.0

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()  # type: ignore[call-arg]  # value is loaded from .env
