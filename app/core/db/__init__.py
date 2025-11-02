# Export base classes only to avoid circular imports
# Models should be imported from their respective modules, not from here

from app.core.db.base import Base, BaseModel

__all__ = ["Base", "BaseModel"]
