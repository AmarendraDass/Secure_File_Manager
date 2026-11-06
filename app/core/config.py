from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = "Secure File Manager"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-only-insecure-secret-change-before-deploy"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, gt=0)

    SQLALCHEMY_DATABASE_URL: str = Field(
        default="sqlite:///./app.db",
        validation_alias="DATABASE_URL",
    )
    STORAGE_BACKEND: Literal["local", "vercel_blob"] = "local"
    UPLOAD_DIR: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[1] / "uploads",
        validation_alias="UPLOAD_DIR",
    )
    MAX_UPLOAD_SIZE_BYTES: int = Field(default=4 * 1024 * 1024, gt=0)
    ALLOWED_ORIGINS: str = ""
    ALLOWED_HOSTS: str = ""


settings = Settings()
