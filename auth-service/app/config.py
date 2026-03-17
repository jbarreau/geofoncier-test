from geofoncier_shared.fastapi.config_mixin import PublicKeyMixin
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(PublicKeyMixin, BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://geofoncier:geofoncier@localhost/geofoncier"
    )
    redis_url: str = "redis://localhost:6379"

    jwt_private_key: str = ""
    jwt_private_key_path: str = ""
    # jwt_public_key, jwt_public_key_path, public_key_content inherited from PublicKeyMixin

    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    @property
    def private_key_content(self) -> str:
        if self.jwt_private_key:
            return self.jwt_private_key
        if self.jwt_private_key_path:
            with open(self.jwt_private_key_path) as f:
                return f.read()
        raise ValueError(
            "No JWT private key configured (set JWT_PRIVATE_KEY or JWT_PRIVATE_KEY_PATH)"
        )


settings = Settings()
