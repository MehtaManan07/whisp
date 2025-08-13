import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable, Awaitable

REQUEST_ID_TOKEN_HEADER = "x-request-id"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_TOKEN_HEADER)

        if not request_id:
            request_id = str(uuid.uuid4())

        # Attach it to request.state for downstream usage
        request.state.request_id = request_id

        response: Response = await call_next(request)

        # Add it to response headers
        response.headers[REQUEST_ID_TOKEN_HEADER] = request_id

        return response
