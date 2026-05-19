from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class TelegramUser(BaseModel):
    id: int
    is_bot: bool = False
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None

    @property
    def display_name(self) -> str:
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or (self.username or "")


class TelegramChat(BaseModel):
    id: int
    type: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class TelegramReplyTo(BaseModel):
    model_config = ConfigDict(extra="allow")

    message_id: int


class TelegramMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    message_id: int
    date: int
    text: Optional[str] = None
    from_: Optional[TelegramUser] = Field(None, alias="from")
    chat: TelegramChat
    reply_to_message: Optional[TelegramReplyTo] = None


class TelegramUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    update_id: int
    message: Optional[TelegramMessage] = None
    edited_message: Optional[TelegramMessage] = None
