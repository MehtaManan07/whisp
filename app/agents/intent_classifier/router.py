import importlib
import pkgutil
import inspect
from pathlib import Path

from app.agents.intent_classifier.decorators import INTENT_REGISTRY
from app.agents.intent_classifier.types import IntentClassificationResult

HANDLER_CLASSES = {}


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
    db,
    redis=None,
    scheduler=None,
):
    for cls_name, handlers in INTENT_REGISTRY.items():
        if intent_result.intent.value in handlers:
            handler_cls = HANDLER_CLASSES[cls_name]
            handler_instance = handler_cls()
            method_name = handlers[intent_result.intent.value]
            method = getattr(handler_instance, method_name)
            return await method(
                intent_result=intent_result,
                user_id=user_id,
                db=db,
            )

    raise ValueError(f"No handler found for intent {intent_result.intent}")
