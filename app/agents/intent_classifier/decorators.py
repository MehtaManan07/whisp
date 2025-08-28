from typing import Dict, Callable, Any, TypeVar
from app.agents.intent_classifier.types import IntentType, IntentHandlerProtocol

# Type definitions for the intent registry
IntentHandlerMap = Dict[IntentType, str]  # Maps intent to method name
IntentRegistry = Dict[str, IntentHandlerMap]  # Maps class name to intent handler map

# Type-safe global registry
INTENT_REGISTRY: IntentRegistry = {}

# Generic type for handler functions - using Callable to preserve function attributes
F = TypeVar('F', bound=Callable[..., Any])


def intent_handler(intent_name: IntentType) -> Callable[[F], F]:
    """Decorator to register class methods as intent handlers."""

    def decorator(func: F) -> F:
        cls_name = func.__qualname__.split(".")[0]
        if cls_name not in INTENT_REGISTRY:
            INTENT_REGISTRY[cls_name] = {}
        INTENT_REGISTRY[cls_name][intent_name] = func.__name__
        return func

    return decorator
