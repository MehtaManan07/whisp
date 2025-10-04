# Error Handling System

This document describes the comprehensive error handling system implemented across the entire codebase.

## Overview

The error handling system provides:
- **Centralized error handling** with consistent error responses
- **Proper HTTP status codes** for different error types
- **User-friendly error messages** that don't expose internal details
- **Detailed logging** for debugging and monitoring
- **Structured error responses** with request IDs for tracking

## Architecture

### 1. Custom Exception Classes (`app/core/exceptions.py`)

The system defines specific exception classes for different error types:

#### Base Exception
- `BaseAppException`: Base class for all application exceptions

#### Domain-Specific Exceptions
- `ValidationError`: Input validation failures (422)
- `NotFoundError`: Resource not found (404)
- `ConflictError`: Resource conflicts (409)
- `UnauthorizedError`: Authentication failures (401)
- `ForbiddenError`: Authorization failures (403)
- `ExternalServiceError`: External API failures (502)
- `DatabaseError`: Database operation failures (500)
- `BusinessLogicError`: Business rule violations (400)
- `RateLimitError`: Rate limit exceeded (429)

#### Specific Domain Exceptions
- `ExpenseNotFoundError`: Expense not found
- `UserNotFoundError`: User not found
- `CategoryNotFoundError`: Category not found
- `WhatsAppAPIError`: WhatsApp API failures
- `LLMServiceError`: LLM service failures
- `LLMTimeoutError`: LLM service timeouts
- `LLMAPIError`: LLM API errors

### 2. Centralized Error Handler (`app/core/error_handler.py`)

The `ErrorHandler` class provides:
- **Standardized error responses** with consistent structure
- **Proper logging** with context and request IDs
- **Debug mode support** for development vs production
- **Exception type routing** to appropriate handlers

#### Error Response Format
```json
{
  "error": {
    "message": "User-friendly error message",
    "status_code": 404,
    "request_id": "uuid-here",
    "code": "UserNotFoundError",
    "details": { /* Only in debug mode */ }
  }
}
```

### 3. Global Exception Handler

The global exception handler in `main.py` catches all unhandled exceptions and routes them through the centralized error handler.

## Usage Examples

### In Controllers

```python
from app.core.exceptions import ValidationError, UserNotFoundError

@router.get("/users/{user_id}")
async def get_user(user_id: int, db: DatabaseDep, user_service: UserServiceDep):
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")
    
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise UserNotFoundError(user_id)
    
    return UserResponseDto.model_validate(user)
```

### In Services

```python
from app.core.exceptions import DatabaseError, ExpenseNotFoundError

async def delete_expense(self, db: AsyncSession, data: DeleteExpenseModel):
    try:
        expense = await db.scalar(select(Expense).where(Expense.id == data.id))
        if not expense:
            raise ExpenseNotFoundError(data.id)
        
        expense.deleted_at = utc_now()
        await db.commit()
    except Exception as e:
        await db.rollback()
        if isinstance(e, ExpenseNotFoundError):
            raise
        raise DatabaseError("delete expense", str(e))
```

### In External Services

```python
from app.core.exceptions import WhatsAppAPIError

async def send_text(self, to: str, text: str):
    if not to or not to.strip():
        raise ValidationError("Recipient phone number is required")
    
    try:
        # API call logic
        response = await client.post(url, json=payload)
        if not response.is_success:
            raise WhatsAppAPIError(f"Failed to send message: {error_message}")
    except httpx.RequestError as e:
        raise WhatsAppAPIError(f"Network error: {str(e)}")
```

## Error Response Examples

### Validation Error (422)
```json
{
  "error": {
    "message": "Invalid input provided",
    "status_code": 422,
    "request_id": "req-123",
    "code": "ValidationError"
  }
}
```

### Not Found Error (404)
```json
{
  "error": {
    "message": "User not found",
    "status_code": 404,
    "request_id": "req-123",
    "code": "UserNotFoundError"
  }
}
```

### External Service Error (502)
```json
{
  "error": {
    "message": "Service temporarily unavailable",
    "status_code": 502,
    "request_id": "req-123",
    "code": "WhatsAppAPIError"
  }
}
```

### Internal Server Error (500)
```json
{
  "error": {
    "message": "Database operation failed",
    "status_code": 500,
    "request_id": "req-123",
    "code": "DatabaseError"
  }
}
```

## Configuration

### Debug Mode
Set debug mode to show detailed error information:

```python
from app.core.error_handler import set_debug_mode

# Enable debug mode (development)
set_debug_mode(True)

# Disable debug mode (production)
set_debug_mode(False)
```

### Environment Variables
- `DEBUG`: Set to `true` to enable debug mode
- `LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)

## Best Practices

### 1. Use Specific Exception Types
```python
# Good
raise UserNotFoundError(user_id)

# Avoid
raise Exception("User not found")
```

### 2. Provide Context in Error Messages
```python
# Good
raise ValidationError("Amount must be greater than 0")

# Avoid
raise ValidationError("Invalid input")
```

### 3. Handle Database Transactions Properly
```python
try:
    # Database operations
    await db.commit()
except Exception as e:
    await db.rollback()
    raise DatabaseError("operation name", str(e))
```

### 4. Log Errors with Context
```python
logger.error(
    f"Database error during expense creation: {str(e)}",
    extra={
        "user_id": user_id,
        "expense_id": expense_id,
        "operation": "create_expense"
    }
)
```

### 5. Don't Expose Internal Details
```python
# Good - User-friendly message
raise ExternalServiceError("WhatsApp API", "Rate limit exceeded")

# Avoid - Exposing internal details
raise ExternalServiceError("WhatsApp API", "API key invalid: sk-123...")
```

## Testing

Use the provided test script to verify error handling:

```bash
python test_error_handling.py
```

The test script covers:
- Validation errors
- Not found errors
- Invalid endpoints
- External service errors

## Monitoring and Logging

All errors are logged with:
- **Request ID** for tracing
- **Error type** and message
- **Stack trace** (in debug mode)
- **Context information** (user ID, operation, etc.)

### Log Format
```
ERROR: Application error: User with ID 123 not found
Extra: {
  "request_id": "req-123",
  "status_code": 404,
  "path": "/users/123",
  "method": "GET",
  "user_id": 123
}
```

## Migration Guide

### Before (Old Error Handling)
```python
try:
    result = await service.operation()
    return result
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

### After (New Error Handling)
```python
# Controllers: Use specific exceptions
if not user_id:
    raise ValidationError("User ID is required")

result = await service.operation()  # Service handles its own errors
return result

# Services: Handle and re-raise with context
try:
    # operation logic
    await db.commit()
except Exception as e:
    await db.rollback()
    raise DatabaseError("operation name", str(e))
```

## Benefits

1. **Consistency**: All errors follow the same format
2. **Security**: No internal details exposed to users
3. **Debugging**: Comprehensive logging with context
4. **Monitoring**: Request IDs for error tracking
5. **User Experience**: Clear, actionable error messages
6. **Maintainability**: Centralized error handling logic
7. **Type Safety**: Specific exception types for different scenarios

## Future Enhancements

- **Error metrics**: Track error rates by type
- **Retry logic**: Automatic retry for transient errors
- **Circuit breakers**: Prevent cascade failures
- **Error notifications**: Alert on critical errors
- **Error recovery**: Automatic recovery mechanisms
