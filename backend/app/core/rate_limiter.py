import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class InMemoryRateLimiter:
    def __init__(self):
        self.requests: Dict[str, list] = {}

    def check(self, key: str, max_requests: int = 60, window_seconds: int = 60) -> Tuple[bool, int]:
        now = time.time()
        if key not in self.requests:
            self.requests[key] = []

        self.requests[key] = [t for t in self.requests[key] if now - t < window_seconds]

        if len(self.requests[key]) >= max_requests:
            return False, max_requests

        self.requests[key].append(now)
        remaining = max_requests - len(self.requests[key])
        return True, remaining


rate_limiter = InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/docs") or request.url.path.startswith("/redoc") or request.url.path.startswith("/openapi"):
            return await call_next(request)

        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{request.url.path}"

        allowed, remaining = rate_limiter.check(key, self.max_requests, self.window_seconds)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests", "retry_after": self.window_seconds},
                headers={"X-RateLimit-Limit": str(self.max_requests), "X-RateLimit-Remaining": "0"},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
