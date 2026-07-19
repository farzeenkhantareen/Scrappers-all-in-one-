"""
Application configuration using Pydantic Settings.
Reads from environment variables and .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # ─────────────────────────────────────────────────────────────
    # App
    # ─────────────────────────────────────────────────────────────
    APP_NAME: str = "Scrappers Dashboard"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=True, env="DEBUG")
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")

    # ─────────────────────────────────────────────────────────────
    # Database
    # ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./scrappers.db", env="DATABASE_URL")
    DATABASE_ECHO: bool = False

    # ─────────────────────────────────────────────────────────────
    # Redis & Celery
    # ─────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/1", env="CELERY_RESULT_BACKEND")

    # ─────────────────────────────────────────────────────────────
    # CORS
    # ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # ─────────────────────────────────────────────────────────────
    # Scraping Defaults
    # ─────────────────────────────────────────────────────────────
    DEFAULT_MAX_PAGES: int = 100
    DEFAULT_MAX_DEPTH: int = 5
    DEFAULT_CONCURRENCY: int = 5
    DEFAULT_DELAY_MS: int = 1000
    DEFAULT_TIMEOUT_SEC: int = 30
    DEFAULT_MAX_RETRIES: int = 3
    DEFAULT_RESPECT_ROBOTS: bool = True
    HEADLESS_BROWSER: bool = True

    # ─────────────────────────────────────────────────────────────
    # User Agent
    # ─────────────────────────────────────────────────────────────
    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # ─────────────────────────────────────────────────────────────
    # Storage
    # ─────────────────────────────────────────────────────────────
    MEDIA_DIR: str = Field(default="./media", env="MEDIA_DIR")
    EXPORT_DIR: str = Field(default="./exports", env="EXPORT_DIR")

    # ─────────────────────────────────────────────────────────────
    # Proxy (optional)
    # ─────────────────────────────────────────────────────────────
    PROXY_URL: Optional[str] = Field(default=None, env="PROXY_URL")
    PROXY_USERNAME: Optional[str] = Field(default=None, env="PROXY_USERNAME")
    PROXY_PASSWORD: Optional[str] = Field(default=None, env="PROXY_PASSWORD")

    # ─────────────────────────────────────────────────────────────
    # Authentication (optional)
    # ─────────────────────────────────────────────────────────────
    INSTAGRAM_USERNAME: Optional[str] = Field(default=None, env="INSTAGRAM_USERNAME")
    INSTAGRAM_PASSWORD: Optional[str] = Field(default=None, env="INSTAGRAM_PASSWORD")
    LINKEDIN_USERNAME: Optional[str] = Field(default=None, env="LINKEDIN_USERNAME")
    LINKEDIN_PASSWORD: Optional[str] = Field(default=None, env="LINKEDIN_PASSWORD")
    GEMINI_API_KEY: Optional[str] = Field(default=None, env="GEMINI_API_KEY")

    class Config:
        env_file = (".env", "../.env")
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()

# Ensure storage directories exist
os.makedirs(settings.MEDIA_DIR, exist_ok=True)
os.makedirs(settings.EXPORT_DIR, exist_ok=True)
