from fastapi import APIRouter, Depends

from app.core.dependencies import (
    DatabaseDep,
    KraftcultureServiceDep,
)
from app.modules.kraftculture.dto import (
    ProcessEmailsRequest,
    ProcessEmailsResponse,
)

router = APIRouter(prefix="/kraftculture", tags=["kraftculture"])


@router.post("/process", response_model=ProcessEmailsResponse)
async def process_kraftculture_emails(
    db: DatabaseDep,
    kraftculture_service: KraftcultureServiceDep,
    request: ProcessEmailsRequest = None,
) -> ProcessEmailsResponse:
    """
    Process Kraftculture emails and send them to WhatsApp.
    
    Fetches emails after the last processed date (stored in cache),
    parses order details, stores in database, and sends to WhatsApp.
    Skips already-processed emails by checking gmail_message_id.
    """
    if request is None:
        request = ProcessEmailsRequest()
    
    return await kraftculture_service.process_emails(
        db=db,
        from_email=request.from_email,
        max_results=request.max_results,
    )


@router.get("/health")
async def kraftculture_health() -> dict:
    """Health check endpoint for kraftculture module."""
    return {"status": "ok", "module": "kraftculture"}
