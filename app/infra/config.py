from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Config(BaseSettings):
    # Database Configuration
    db_url: str = Field(default="", alias="DB_URL")

    # WhatsApp Configuration
    wa_verify_token: str = Field(default="", alias="WA_VERIFY_TOKEN")
    wa_access_token: str = Field(default="", alias="WA_ACCESS_TOKEN")
    wa_phone_number_id: str = Field(default="", alias="WA_PHONE_NUMBER_ID")

    # LLM (Language Model) Configuration
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    open_router_api_key: str = Field(default="", alias="OPEN_ROUTER_API_KEY")
    open_router_model_name: str = Field(
        default="deepseek/deepseek-chat-v3-0324:free", alias="OPEN_ROUTER_MODEL_NAME"
    )
    is_production: bool = os.getenv("ENVIRONMENT", "development").lower() == "production"

    # Path to .env file (for loading env vars)
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instantiate the settings
config = Config()
