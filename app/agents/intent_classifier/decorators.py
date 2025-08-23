INTENT_REGISTRY = {}


def intent_handler(intent_name: str):
    """Decorator to register class methods as intent handlers."""

    def decorator(func):
        cls = func.__qualname__.split(".")[0]
        if cls not in INTENT_REGISTRY:
            INTENT_REGISTRY[cls] = {}
        INTENT_REGISTRY[cls][intent_name] = func.__name__
        return func

    return decorator
