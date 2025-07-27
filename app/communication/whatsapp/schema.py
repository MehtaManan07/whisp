from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class WebhookContact(BaseModel):
    profile: dict[str, str]  # {"name": "John Doe"}
    wa_id: str


class WebhookMessageText(BaseModel):
    body: str


class WebhookMessageImage(BaseModel):
    mime_type: str
    sha256: str
    id: str


class WebhookMessageContext(BaseModel):
    from_: str = Field(alias="from")  # 'from' is reserved keyword
    id: str


class WebhookMessage(BaseModel):
    from_: str = Field(alias="from")  # Handle reserved keyword
    id: str
    timestamp: str
    type: Literal["text", "image"]
    text: Optional[WebhookMessageText] = None
    image: Optional[WebhookMessageImage] = None
    context: Optional[WebhookMessageContext] = None


class WebhookStatusConversation(BaseModel):
    id: str
    expiration_timestamp: Optional[str] = None
    origin: dict[str, str]  # {"type": "service"}


class WebhookStatusPricing(BaseModel):
    billable: bool
    pricing_model: str
    category: str
    type: str


class WebhookStatus(BaseModel):
    id: str
    status: Literal["sent", "delivered", "read", "failed"]
    timestamp: str
    recipient_id: str
    conversation: WebhookStatusConversation
    pricing: Optional[WebhookStatusPricing] = None


class WebhookMetadata(BaseModel):
    display_phone_number: str
    phone_number_id: str


class WebhookValue(BaseModel):
    messaging_product: Literal["whatsapp"]
    metadata: WebhookMetadata
    contacts: Optional[List[WebhookContact]] = None
    messages: Optional[List[WebhookMessage]] = None
    statuses: Optional[List[WebhookStatus]] = None


class WebhookChange(BaseModel):
    field: Literal["messages"]
    value: WebhookValue


class WebhookEntry(BaseModel):
    id: str
    changes: List[WebhookChange]


class WebhookPayload(BaseModel):
    object: Literal["whatsapp_business_account"]
    entry: List[WebhookEntry]

    class Config:
        # Allow field aliases (for 'from' keyword)
        validate_by_name = True


class ProcessMessageResult(BaseModel):
    messages: List[str]  # What to send back to the user
    status: Literal["success", "error"]  # Basic status for control/logging


class HandleMessagePayload(BaseModel):
    from_: str = Field(alias="from")
    contact: "WebhookContact"
    message: "WebhookMessage"
