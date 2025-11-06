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
    wa_app_id: str = Field(default="", alias="WA_APP_ID")
    wa_app_secret: str = Field(default="", alias="WA_APP_SECRET")
    
    cron_keys: str = Field(default="", alias="CRON_KEYS")
    
    # Redis Configuration
    redis_url: str = Field(default="", alias="UPSTASH_REDIS_REST_URL")
    redis_token: str = Field(default="", alias="UPSTASH_REDIS_REST_TOKEN")
    redis_host: str = Field(default="", alias="UPSTASH_REDIS_HOST")
    redis_port: int = Field(default=0, alias="UPSTASH_REDIS_PORT")
    
    # AWS EventBridge Scheduler Configuration
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")
    eventbridge_role_arn: str = Field(default="", alias="EVENTBRIDGE_ROLE_ARN")  # IAM role for EventBridge to invoke HTTP targets
    app_base_url: str = Field(default="", alias="APP_BASE_URL")  # Your app URL for webhook callbacks
    
    # Reminders Process Token (for cron job authentication)
    reminders_process_token: str = Field(default="", alias="REMINDERS_PROCESS_TOKEN")

    # LLM (Language Model) Configuration
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    open_router_api_key: str = Field(default="", alias="OPEN_ROUTER_API_KEY")
    open_router_api_keys: str = Field(default="", alias="OPEN_ROUTER_API_KEYS")  # Comma-separated list of API keys
    open_router_daily_limit: int = Field(default=50, alias="OPEN_ROUTER_DAILY_LIMIT")  # Daily limit per key
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
