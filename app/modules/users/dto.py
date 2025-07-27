from pydantic import BaseModel
from typing import Optional, Dict, Any


class CreateUserDto(BaseModel):
    wa_id: str
    name: Optional[str] = None
    phone_number: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
