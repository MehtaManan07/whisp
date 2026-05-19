from pydantic import BaseModel, Field


class SendMessageDto(BaseModel):
    chat_id: str = Field(..., description="Telegram chat ID to send the message to")
    message: str = Field(..., description="The message content to send")
