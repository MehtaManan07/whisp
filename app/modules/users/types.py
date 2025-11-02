from typing import TypedDict

from app.modules.users.models import User


class FindOrCreateResult(TypedDict):
    user: User
    is_existing_user: bool
