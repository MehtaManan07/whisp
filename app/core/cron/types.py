from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from enum import IntEnum


# Enums for JobStatus, JobType, RequestMethod
class JobStatus(IntEnum):
    UNKNOWN = 0
    OK = 1
    FAILED_DNS = 2
    FAILED_CONNECT = 3
    FAILED_HTTP = 4
    FAILED_TIMEOUT = 5
    FAILED_TOO_MUCH_DATA = 6
    FAILED_INVALID_URL = 7
    FAILED_INTERNAL = 8
    FAILED_UNKNOWN = 9


class JobType(IntEnum):
    DEFAULT = 0
    MONITORING = 1


class RequestMethod(IntEnum):
    GET = 0
    POST = 1
    PUT = 2
    DELETE = 3


# JobSchedule model
class JobSchedule(BaseModel):
    timezone: Optional[str] = "UTC"
    expiresAt: Optional[int] = 0
    hours: Optional[List[int]] = []
    mdays: Optional[List[int]] = []
    minutes: Optional[List[int]] = []
    months: Optional[List[int]] = []
    wdays: Optional[List[int]] = []


# JobExtendedData model
class JobExtendedData(BaseModel):
    headers: Optional[Dict[str, str]] = {}
    body: Optional[str] = ""


# JobAuth model
class JobAuth(BaseModel):
    enable: Optional[bool] = False
    user: Optional[str] = ""
    password: Optional[str] = ""


# JobNotificationSettings model
class JobNotificationSettings(BaseModel):
    onFailure: Optional[bool] = False
    onFailureCount: Optional[int] = 1
    onSuccess: Optional[bool] = False
    onDisable: Optional[bool] = False


# Job model
class Job(BaseModel):
    jobId: Optional[int] = None  # read-only
    enabled: Optional[bool] = False
    title: Optional[str] = ""
    saveResponses: Optional[bool] = False
    url: str  # mandatory
    lastStatus: Optional[JobStatus] = JobStatus.UNKNOWN  # read-only
    lastDuration: Optional[int] = None  # read-only
    lastExecution: Optional[int] = None  # read-only
    nextExecution: Optional[int] = None  # read-only
    type: Optional[JobType] = JobType.DEFAULT  # read-only
    requestTimeout: Optional[int] = -1
    redirectSuccess: Optional[bool] = False
    folderId: Optional[int] = 0
    schedule: Optional[JobSchedule] = JobSchedule()
    requestMethod: Optional[RequestMethod] = RequestMethod.GET


class DetailedJob(Job):
    auth: Optional[JobAuth] = None
    notification: Optional[JobNotificationSettings] = None
    extendedData: Optional[JobExtendedData] = None


class JobsListResponse(BaseModel):
    """Response from GET /jobs endpoint."""

    jobs: List[Job] = Field(..., description="List of jobs present in the account")
    someFailed: bool = Field(
        ...,
        description="True if some jobs could not be retrieved due to internal errors",
    )


class JobDetailsResponse(BaseModel):
    """Response from GET /jobs/<jobId> endpoint."""

    jobDetails: DetailedJob = Field(..., description="Job details")


class CreateJobResponse(BaseModel):
    """Response from PUT /jobs endpoint."""

    jobId: int = Field(..., description="Identifier of the created job")


class UpdateJobResponse(BaseModel):
    """Response from PATCH /jobs/<jobId> endpoint (empty object)."""

    pass


class DeleteJobResponse(BaseModel):
    """Response from DELETE /jobs/<jobId> endpoint (empty object)."""

    pass
