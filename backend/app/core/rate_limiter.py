import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timezone


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


class DailyUsageTracker:
    """Tracks daily API usage per user for subscription limits."""

    def __init__(self):
        self._data: Dict[int, list] = {}

    def _today_key(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def check(self, user_id: int, max_daily: int) -> Tuple[bool, int]:
        key = self._today_key()
        user_key = f"{user_id}:{key}"

        now = time.time()
        if user_key not in self._data:
            self._data[user_key] = []

        today_ts = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        self._data[user_key] = [t for t in self._data[user_key] if t >= today_ts]

        used = len(self._data[user_key])
        if used >= max_daily:
            return False, 0

        self._data[user_key].append(now)
        return True, max_daily - used - 1

    def daily_usage(self, user_id: int) -> int:
        key = self._today_key()
        user_key = f"{user_id}:{key}"
        today_ts = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        self._data[user_key] = [t for t in self._data.get(user_key, []) if t >= today_ts]
        return len(self._data.get(user_key, []))


daily_tracker = DailyUsageTracker()


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
