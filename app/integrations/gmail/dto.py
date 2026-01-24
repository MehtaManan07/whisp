from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class EmailDTO(BaseModel):
    """DTO representing an email message."""
    
    id: str = Field(..., description="Gmail message ID")
    thread_id: str = Field(..., description="Gmail thread ID")
    subject: str = Field(default="", description="Email subject")
    from_email: str = Field(default="", description="Sender email address")
    from_name: str = Field(default="", description="Sender display name")
    to_email: str = Field(default="", description="Recipient email address")
    body: str = Field(default="", description="Email body (plain text)")
    html_body: Optional[str] = Field(default=None, description="Email body (HTML)")
    date: Optional[datetime] = Field(default=None, description="Email date")
    snippet: str = Field(default="", description="Email snippet/preview")
    is_unread: bool = Field(default=True, description="Whether email is unread")
    labels: list[str] = Field(default_factory=list, description="Gmail labels")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "18d1234567890abc",
                "thread_id": "18d1234567890abc",
                "subject": "Order Confirmation",
                "from_email": "orders@example.com",
                "from_name": "Example Store",
                "to_email": "user@gmail.com",
                "body": "Thank you for your order...",
                "date": "2026-01-24T10:00:00Z",
                "snippet": "Thank you for your order...",
                "is_unread": True,
                "labels": ["INBOX", "UNREAD"],
            }
        }


class FetchEmailsRequest(BaseModel):
    """Request DTO for fetching emails."""
    
    from_email: Optional[str] = Field(default=None, description="Filter by sender email")
    subject_contains: Optional[str] = Field(default=None, description="Filter by subject containing text")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of emails to fetch")
    unread_only: bool = Field(default=False, description="Only fetch unread emails")
    
    class Config:
        json_schema_extra = {
            "example": {
                "from_email": "orders@kraftculture.com",
                "max_results": 5,
                "unread_only": True,
            }
        }
