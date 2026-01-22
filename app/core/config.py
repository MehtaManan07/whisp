from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Config(BaseSettings):
    # Database Configuration - SQLite
    db_url: str = Field(
        default="sqlite+aiosqlite:///whisp.db", 
        alias="DB_URL"
    )

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
    
    
    

    # Path to .env file (for loading env vars)
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Instantiate the settings
config = Config()
