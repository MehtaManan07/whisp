"""
Custom exception classes for the application.
These provide structured error handling with proper HTTP status codes and user-friendly messages.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class BaseAppException(Exception):
    """Base exception class for all application-specific exceptions."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.user_message = user_message or message
        super().__init__(self.message)


class ValidationError(BaseAppException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
            user_message=message  # Use the actual validation message
        )


class NotFoundError(BaseAppException):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: Any, details: Optional[Dict[str, Any]] = None):
        message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
            user_message=f"{resource_type} not found"
        )


class ConflictError(BaseAppException):
    """Raised when there's a conflict with existing data."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
            user_message="Resource conflict occurred"
        )


class UnauthorizedError(BaseAppException):
    """Raised when authentication or authorization fails."""
    
    def __init__(self, message: str = "Unauthorized access", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
            user_message="Access denied"
        )


class ForbiddenError(BaseAppException):
    """Raised when access is forbidden."""
    
    def __init__(self, message: str = "Forbidden", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
            user_message="Access forbidden"
        )


class ExternalServiceError(BaseAppException):
    """Raised when external service calls fail."""
    
    def __init__(self, service_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        full_message = f"External service error ({service_name}): {message}"
        super().__init__(
            message=full_message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
            user_message=f"Service temporarily unavailable"
        )


class DatabaseError(BaseAppException):
    """Raised when database operations fail."""
    
    def __init__(self, operation: str, message: str, details: Optional[Dict[str, Any]] = None):
        full_message = f"Database error during {operation}: {message}"
        super().__init__(
            message=full_message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            user_message="Database operation failed"
        )


class BusinessLogicError(BaseAppException):
    """Raised when business logic validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            user_message=message
        )


class RateLimitError(BaseAppException):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
            user_message="Too many requests, please try again later"
        )


# Specific domain exceptions
class ExpenseNotFoundError(NotFoundError):
    """Raised when an expense is not found."""
    
    def __init__(self, expense_id: int, details: Optional[Dict[str, Any]] = None):
        super().__init__("Expense", expense_id, details)


class UserNotFoundError(NotFoundError):
    """Raised when a user is not found."""
    
    def __init__(self, user_id: Any, details: Optional[Dict[str, Any]] = None):
        super().__init__("User", user_id, details)


class CategoryNotFoundError(NotFoundError):
    """Raised when a category is not found."""
    
    def __init__(self, category_id: Any, details: Optional[Dict[str, Any]] = None):
        super().__init__("Category", category_id, details)


class WhatsAppAPIError(ExternalServiceError):
    """Raised when WhatsApp API calls fail."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("WhatsApp API", message, details)


class LLMServiceError(ExternalServiceError):
    """Raised when LLM service calls fail."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("LLM Service", message, details)


class LLMTimeoutError(LLMServiceError):
    """Raised when LLM service times out."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Timeout: {message}", details)


class LLMAPIError(LLMServiceError):
    """Raised when LLM API returns an error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"API Error: {message}", details)
