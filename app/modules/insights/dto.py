from typing import Optional
from pydantic import BaseModel, Field


class GetInsightsModel(BaseModel):
    user_id: int = Field(description="The user's ID")
    period: Optional[str] = Field(
        None,
        description="Time period for insights: this_week, last_week, this_month, last_month",
    )
    compare: bool = Field(
        False,
        description="Whether to include comparison with previous period",
    )
