from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Config(BaseSettings):
    # Database Configuration - Turso (libSQL)
    turso_database_url: str = Field(alias="TURSO_DATABASE_URL")
    turso_auth_token: str = Field(alias="TURSO_AUTH_TOKEN")

    # WhatsApp Configuration
    wa_verify_token: str = Field(default="", alias="WA_VERIFY_TOKEN")
    wa_access_token: str = Field(default="", alias="WA_ACCESS_TOKEN")
    wa_phone_number_id: str = Field(default="", alias="WA_PHONE_NUMBER_ID")
    wa_app_id: str = Field(default="", alias="WA_APP_ID")
    wa_app_secret: str = Field(default="", alias="WA_APP_SECRET")
    
    cron_keys: str = Field(default="", alias="CRON_KEYS")

    app_base_url: str = Field(default="", alias="APP_BASE_URL")  # Your app URL for webhook callbacks
    
    # Reminders Process Token (for cron job authentication)
    reminders_process_token: str = Field(default="", alias="REMINDERS_PROCESS_TOKEN")

    # LLM (Language Model) Configuration
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    gemini_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model_name: str = Field(
        default="gemini-3-flash-preview", alias="GEMINI_MODEL_NAME"
    )
    is_production: bool = os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    # Gmail Configuration
    gmail_credentials_path: str = Field(
        default="credentials.json", alias="GMAIL_CREDENTIALS_PATH"
    )
    gmail_token_path: str = Field(
        default="token.json", alias="GMAIL_TOKEN_PATH"
    )
    
    # Kraftculture Configuration
    kraftculture_whatsapp_numbers: str = Field(
        default="919328483009", alias="KRAFTCULTURE_WHATSAPP_NUMBERS"
    )
    kraftculture_sender_email: str = Field(
        default="", alias="KRAFTCULTURE_SENDER_EMAIL"
    )
    
    # Scheduler Configuration (APScheduler)
    scheduler_enabled: bool = Field(
        default=True, alias="SCHEDULER_ENABLED"
    )
    scheduler_reminders_interval_minutes: int = Field(
        default=1, alias="SCHEDULER_REMINDERS_INTERVAL_MINUTES"
    )
    scheduler_kraftculture_interval_hours: int = Field(
        default=1, alias="SCHEDULER_KRAFTCULTURE_INTERVAL_HOURS"
    )

    # Path to .env file (for loading env vars)
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Instantiate the settings
config = Config()
