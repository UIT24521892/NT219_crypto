"""
Citizen Services Portal — Application settings.
Loaded from .env via pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str

    # JWT (sẽ generate ở step sau)
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60

    # Upload
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10


settings = Settings()
