from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings() # type: ignore[call-arg]  # value is loaded from .env