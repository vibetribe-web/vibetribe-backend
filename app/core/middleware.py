import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger("app.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        is_preflight = request.method == "OPTIONS" and "access-control-request-method" in request.headers
        if is_preflight:
            origin = request.headers.get("origin", "<missing>")
            requested_method = request.headers.get("access-control-request-method", "<missing>")
            requested_headers = request.headers.get("access-control-request-headers", "<none>")
            log_method = logger.warning if response.status_code >= 400 else logger.info
            log_method(
                "CORS preflight %s origin=%s requested_method=%s requested_headers=%s -> %s %.2fms",
                request.url.path,
                origin,
                requested_method,
                requested_headers,
                response.status_code,
                elapsed_ms,
            )
        logger.info(
            "%s %s -> %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
