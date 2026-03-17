from geofoncier_shared.config_mixin import PublicKeyMixin
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(PublicKeyMixin, BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379"
    # jwt_public_key, jwt_public_key_path, public_key_content inherited from PublicKeyMixin


settings = Settings()
