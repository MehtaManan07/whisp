from pydantic import BaseModel, Field


class VerifyWebhookDto(BaseModel):
    hub_mode: str = Field(alias="hub.mode")
    hub_verify_token: str = Field(alias="hub.verify_token")
    hub_challenge: str = Field(alias="hub.challenge")

    class Config:
        validate_by_name = True


class SendMessageDto(BaseModel):
    recipient: str
    message: str
