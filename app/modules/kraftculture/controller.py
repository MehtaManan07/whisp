from fastapi import APIRouter, Depends

from app.core.dependencies import (
    KraftcultureServiceDep,
)
from app.modules.kraftculture.dto import (
    ProcessEmailsRequest,
    ProcessEmailsResponse,
)

router = APIRouter(prefix="/kraftculture", tags=["kraftculture"])


@router.post("/process", response_model=ProcessEmailsResponse)
async def process_kraftculture_emails(
    kraftculture_service: KraftcultureServiceDep,
    request: ProcessEmailsRequest = None,
) -> ProcessEmailsResponse:
    """
    Process Kraftculture emails and send them to WhatsApp.
    """
    if request is None:
        request = ProcessEmailsRequest()

    return await kraftculture_service.process_emails(
        from_email=request.from_email,
        max_results=request.max_results,
    )


@router.get("/health")
async def kraftculture_health() -> dict:
    """Health check endpoint for kraftculture module."""
    return {"status": "ok", "module": "kraftculture"}
