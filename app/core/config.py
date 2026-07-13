from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Config(BaseSettings):
    # Database Configuration - Turso (libSQL)
    turso_database_url: str = Field(alias="TURSO_DATABASE_URL")
    turso_auth_token: str = Field(alias="TURSO_AUTH_TOKEN")

    # Telegram Configuration
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_secret: str = Field(default="", alias="TELEGRAM_WEBHOOK_SECRET")
    telegram_allowed_user_id: Optional[int] = Field(
        default=None, alias="TELEGRAM_ALLOWED_USER_ID"
    )

    cron_keys: str = Field(default="", alias="CRON_KEYS")

    app_base_url: str = Field(default="", alias="APP_BASE_URL")

    # Reminders Process Token (for cron job authentication)
    reminders_process_token: str = Field(default="", alias="REMINDERS_PROCESS_TOKEN")

    # LLM (Language Model) Configuration
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    gemini_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model_name: str = Field(
        default="gemini-3-flash-preview", alias="GEMINI_MODEL_NAME"
    )
    is_production: bool = os.getenv("ENVIRONMENT", "development").lower() == "production"

    # Scheduler Configuration (APScheduler)
    scheduler_enabled: bool = Field(
        default=True, alias="SCHEDULER_ENABLED"
    )
    scheduler_reminders_interval_minutes: int = Field(
        default=1, alias="SCHEDULER_REMINDERS_INTERVAL_MINUTES"
    )

    # Gmail auto-capture Configuration
    gmail_capture_enabled: bool = Field(default=True, alias="GMAIL_CAPTURE_ENABLED")
    gmail_poll_interval_minutes: int = Field(
        default=15, alias="GMAIL_POLL_INTERVAL_MINUTES"
    )
    gmail_lookback_days: int = Field(default=1, alias="GMAIL_LOOKBACK_DAYS")
    gmail_credentials_path: str = Field(
        default="credentials.json", alias="GMAIL_CREDENTIALS_PATH"
    )
    gmail_token_path: str = Field(default="token.json", alias="GMAIL_TOKEN_PATH")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


config = Config()
