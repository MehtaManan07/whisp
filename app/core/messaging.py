from typing import Optional, Literal, List
from pydantic import BaseModel


class IncomingContact(BaseModel):
    external_id: str
    name: Optional[str] = None


class IncomingMessage(BaseModel):
    id: str
    text: Optional[str] = None
    reply_to_id: Optional[str] = None


class HandleMessagePayload(BaseModel):
    sender_id: str
    contact: IncomingContact
    message: IncomingMessage


class ProcessMessageResult(BaseModel):
    messages: List[str]
    status: Literal["success", "error"]
