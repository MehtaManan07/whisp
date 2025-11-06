from typing import TypedDict

from app.modules.users.models import User


class FindOrCreateResult(TypedDict):
    """Result of finding or creating a user."""
    user: User  # The user object that was found or created
    is_existing_user: bool  # Whether the user already existed or was newly created
