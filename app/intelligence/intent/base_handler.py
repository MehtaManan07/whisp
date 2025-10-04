from typing import Any


class BaseHandlers:
    """All handlers inherit this so they get shared deps injected."""

    def __init__(self):
        print("BaseHandlers init")

    async def handle(
        self,
        func,
        *args,
        **kwargs,
    ) -> Any:
        """
        Generic wrapper so child handlers can get consistent error handling/logging.
        """
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            print(f"Handler error in {func.__name__}: {e}")
            raise
