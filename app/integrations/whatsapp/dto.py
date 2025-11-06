from pydantic import BaseModel, Field


class VerifyWebhookDto(BaseModel):
    hub_mode: str = Field(alias="hub.mode", description="Webhook mode (should be 'subscribe')")
    hub_verify_token: str = Field(alias="hub.verify_token", description="Verification token for webhook authentication")
    hub_challenge: str = Field(alias="hub.challenge", description="Challenge string for webhook verification")

    class Config:
        validate_by_name = True


class SendMessageDto(BaseModel):
    recipient: str = Field(..., description="WhatsApp ID or phone number of the recipient")
    message: str = Field(..., description="Message content to send")
