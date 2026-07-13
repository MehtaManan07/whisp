from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EmailDTO(BaseModel):
    """A single Gmail message, trimmed to what the capture pipeline needs."""

    id: str = Field(..., description="Gmail message ID (stable, used for dedup)")
    thread_id: str = Field(default="", description="Gmail thread ID")
    subject: str = Field(default="", description="Email subject")
    from_email: str = Field(default="", description="Sender email address (lowercased)")
    from_name: str = Field(default="", description="Sender display name")
    date: Optional[datetime] = Field(default=None, description="Email date header")
    internal_date: Optional[int] = Field(
        default=None, description="Gmail internalDate in epoch seconds (checkpoint basis)"
    )
    body: str = Field(default="", description="Plain-text body (HTML stripped if needed)")
    snippet: str = Field(default="", description="Gmail snippet/preview")
