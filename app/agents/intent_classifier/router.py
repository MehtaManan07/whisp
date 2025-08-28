import importlib
import pkgutil
import inspect
from pathlib import Path
from typing import Dict, Type, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.intent_classifier.decorators import INTENT_REGISTRY
from app.agents.intent_classifier.types import IntentClassificationResult
from app.agents.intent_classifier.base_handler import BaseHandlers

# Type-safe handler classes registry
HANDLER_CLASSES: Dict[str, Type[BaseHandlers]] = {}


def discover_handlers():
    """
    Auto-discover all handlers inside app/modules/*/handlers.py
    """
    modules_path = Path(__file__).parent.parent.parent / "modules"
    package = "app.modules"

    for module_info in pkgutil.iter_modules([str(modules_path)]):
        module_name = module_info.name
        handlers_module = f"{package}.{module_name}.handlers"

        try:
            module = importlib.import_module(handlers_module)
        except ModuleNotFoundError:
            continue

        # collect classes inside handlers.py
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ == handlers_module:
                HANDLER_CLASSES[name] = obj


discover_handlers()


async def route_intent(
    intent_result: IntentClassificationResult,
    user_id: int,
    db: AsyncSession,
) -> str:
    """Route intent to appropriate handler with type safety."""
    for cls_name, handlers in INTENT_REGISTRY.items():
        if intent_result.intent in handlers:
            handler_cls: Optional[Type[BaseHandlers]] = HANDLER_CLASSES.get(cls_name)
            if handler_cls is None:
                raise ValueError(f"Handler class {cls_name} not found in registry")

            handler_instance: BaseHandlers = handler_cls()
            method_name: str = handlers[intent_result.intent]

            if not hasattr(handler_instance, method_name):
                raise ValueError(
                    f"Method {method_name} not found in handler {cls_name}"
                )

            method = getattr(handler_instance, method_name)
            return await method(intent_result=intent_result, user_id=user_id, db=db)

    raise ValueError(f"No handler found for intent {intent_result.intent}")
