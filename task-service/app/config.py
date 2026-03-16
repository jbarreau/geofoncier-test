from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://geofoncier:geofoncier@localhost/geofoncier"
    redis_url: str = "redis://localhost:6379"
    jwt_public_key: str = ""
    jwt_public_key_path: str = ""

    @property
    def public_key_content(self) -> str:
        if self.jwt_public_key:
            return self.jwt_public_key
        if self.jwt_public_key_path:
            with open(self.jwt_public_key_path) as f:
                return f.read()
        raise ValueError(
            "No JWT public key configured. Set JWT_PUBLIC_KEY or JWT_PUBLIC_KEY_PATH."
        )


settings = Settings()
