from geofoncier_shared.fastapi import PublicKeyMixin
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(PublicKeyMixin, BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    redis_url: str = "redis://localhost:6379"


settings = Settings()
