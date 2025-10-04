"""
Centralized error handling for the application.
Provides consistent error responses and logging across all endpoints.
"""

import logging
import traceback
from typing import Any, Dict, Optional, Union
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError as PydanticValidationError

from .exceptions import BaseAppException

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling service."""
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
    
    def create_error_response(
        self,
        status_code: int,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> JSONResponse:
        """Create a standardized error response."""
        
        error_response = {
            "error": {
                "message": message,
                "status_code": status_code,
                "request_id": request_id,
            }
        }
        
        if error_code:
            error_response["error"]["code"] = error_code
            
        if details and self.debug_mode:
            error_response["error"]["details"] = details
            
        return JSONResponse(
            status_code=status_code,
            content=error_response
        )
    
    def handle_app_exception(
        self, 
        exc: BaseAppException, 
        request: Request
    ) -> JSONResponse:
        """Handle custom application exceptions."""
        
        # Log the error with context
        logger.error(
            f"Application error: {exc.message}",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "status_code": exc.status_code,
                "details": exc.details,
                "path": request.url.path,
                "method": request.method,
            }
        )
        
        return self.create_error_response(
            status_code=exc.status_code,
            message=exc.user_message,
            details=exc.details if self.debug_mode else None,
            request_id=getattr(request.state, "request_id", None),
            error_code=exc.__class__.__name__
        )
    
    def handle_http_exception(
        self, 
        exc: HTTPException, 
        request: Request
    ) -> JSONResponse:
        """Handle FastAPI HTTP exceptions."""
        
        logger.warning(
            f"HTTP exception: {exc.detail}",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
            }
        )
        
        return self.create_error_response(
            status_code=exc.status_code,
            message=str(exc.detail),
            request_id=getattr(request.state, "request_id", None),
            error_code="HTTPException"
        )
    
    def handle_validation_error(
        self, 
        exc: Union[RequestValidationError, PydanticValidationError], 
        request: Request
    ) -> JSONResponse:
        """Handle validation errors."""
        
        # Extract validation details
        if isinstance(exc, RequestValidationError):
            errors = exc.errors()
            details = {"validation_errors": errors}
            message = "Request validation failed"
        else:
            errors = exc.errors()
            details = {"validation_errors": errors}
            message = "Data validation failed"
        
        logger.warning(
            f"Validation error: {message}",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "path": request.url.path,
                "method": request.method,
                "validation_errors": errors,
            }
        )
        
        return self.create_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=message,
            details=details if self.debug_mode else None,
            request_id=getattr(request.state, "request_id", None),
            error_code="ValidationError"
        )
    
    def handle_database_error(
        self, 
        exc: SQLAlchemyError, 
        request: Request
    ) -> JSONResponse:
        """Handle database errors."""
        
        error_message = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
        
        logger.error(
            f"Database error: {error_message}",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "path": request.url.path,
                "method": request.method,
                "error_type": exc.__class__.__name__,
            },
            exc_info=True
        )
        
        # Don't expose database details in production
        user_message = "Database operation failed"
        if self.debug_mode:
            user_message = f"Database error: {error_message}"
        
        return self.create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=user_message,
            details={"error_type": exc.__class__.__name__} if self.debug_mode else None,
            request_id=getattr(request.state, "request_id", None),
            error_code="DatabaseError"
        )
    
    def handle_generic_exception(
        self, 
        exc: Exception, 
        request: Request
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        
        error_message = str(exc)
        traceback_str = traceback.format_exc()
        
        logger.error(
            f"Unexpected error: {error_message}",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "path": request.url.path,
                "method": request.method,
                "error_type": exc.__class__.__name__,
                "traceback": traceback_str,
            },
            exc_info=True
        )
        
        # Don't expose internal details in production
        user_message = "An unexpected error occurred"
        details = None
        
        if self.debug_mode:
            user_message = error_message
            details = {
                "error_type": exc.__class__.__name__,
                "traceback": traceback_str,
            }
        
        return self.create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=user_message,
            details=details,
            request_id=getattr(request.state, "request_id", None),
            error_code="InternalServerError"
        )


# Global error handler instance
error_handler = ErrorHandler(debug_mode=False)  # Set to True in development


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for FastAPI."""
    
    if isinstance(exc, BaseAppException):
        return error_handler.handle_app_exception(exc, request)
    elif isinstance(exc, HTTPException):
        return error_handler.handle_http_exception(exc, request)
    elif isinstance(exc, (RequestValidationError, PydanticValidationError)):
        return error_handler.handle_validation_error(exc, request)
    elif isinstance(exc, SQLAlchemyError):
        return error_handler.handle_database_error(exc, request)
    else:
        return error_handler.handle_generic_exception(exc, request)


def set_debug_mode(debug: bool) -> None:
    """Set debug mode for error handling."""
    global error_handler
    error_handler = ErrorHandler(debug_mode=debug)
