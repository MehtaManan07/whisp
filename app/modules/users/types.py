from typing import TypedDict

from app.core.db import User


class FindOrCreateResult(TypedDict):
    user: User
    is_existing_user: bool
