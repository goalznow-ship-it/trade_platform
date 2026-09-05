"""
Security headers middleware.

Adds a baseline of HTTP security headers to every response. Without
this, the platform ships with default browser behavior: no
clickjacking protection, no MIME-sniffing guard, no HSTS, and
referrer leakage. None of these are exotic — every modern web app
should send them by default.

Headers added:

- X-Content-Type-Options: nosniff
    Prevents browsers from interpreting files as a different MIME
    type than declared. Without this, an attacker who can upload a
    text/html payload named .csv could get script execution.

- X-Frame-Options: DENY
    Clickjacking protection. Even though the dashboard is SPA and
    not embeddable, denying framing entirely is the safe default.

- Referrer-Policy: strict-origin-when-cross-origin
    Don't leak full URL (with query params that may contain
    tokens) to third-party sites.

- Permissions-Policy: camera=(), microphone=(), geolocation=()
    We don't need any of these, so explicitly disable.

- Strict-Transport-Security: max-age=63072000; includeSubDomains
    Only added in production (HTTPS-terminated). Tells the browser
    to refuse to ever speak plain HTTP to us for 2 years.

- Cross-Origin-Opener-Policy: same-origin
    Isolates the browsing context — protects against Spectre-style
    side-channel attacks from cross-origin popups.
"""
from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        # Always-on headers
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), interest-cohort=()",
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        # HSTS only when we're actually serving HTTPS. Sending HSTS over
        # HTTP is harmless but pointless; in dev/test it can confuse
        # local proxies.
        if settings.ENVIRONMENT == "production" or os.environ.get("FORCE_HSTS"):
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains",
            )
        return response
