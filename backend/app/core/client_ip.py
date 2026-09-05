"""
Client IP detection behind reverse proxies.

When the API runs behind nginx (which is the production setup —
nginx terminates TLS, rate-limits, and forwards to the backend),
request.client.host is the nginx container's IP, not the real
visitor. Every request from the outside world looks like it's
coming from the same 172.x.x.x, which means:

- the per-IP rate limiter in app.core.rate_limiter is a global
  limit, not a per-visitor limit (one attacker DoS-es the API
  for everyone)
- audit logs lose the actual origin IP
- account-lockout-by-IP is useless

The standard fix is to consult X-Forwarded-For, which nginx sets.
But XFF is client-spoofable — anyone can send X-Forwarded-For:
1.2.3.4 and have us believe it. So we trust XFF only when the
request actually came from a known proxy hop.

For the dev default, we trust one hop. In production behind
nginx, set TRUSTED_PROXY_CIDRS=172.16.0.0/12,10.0.0.0/8 (or
the actual docker network range) to restrict the trust.
"""
from __future__ import annotations

import ipaddress
import os

from fastapi import Request


def _trusted_cidrs() -> list:
    raw = os.environ.get("TRUSTED_PROXY_CIDRS", "")
    out: list = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            out.append(ipaddress.ip_network(chunk, strict=False))
        except ValueError:
            pass
    return out


_TRUSTED = _trusted_cidrs()


def _is_trusted_proxy(ip_str: str) -> bool:
    if not _TRUSTED:
        return True  # dev default: trust one hop
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(ip in net for net in _TRUSTED)


def get_client_ip(request: Request) -> str:
    """
    Return the best-guess real client IP. Order:

    1. X-Forwarded-For (leftmost = originating client) if the
       request came from a trusted proxy.
    2. X-Real-IP if the request came from a trusted proxy.
    3. request.client.host as a fallback.

    Returns "unknown" only when there is genuinely no peer info.
    """
    if request.client and request.client.host and _is_trusted_proxy(request.client.host):
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # XFF is a comma-separated list. The leftmost is the
            # original client; the rightmost is the most recent
            # proxy. Take the leftmost.
            first = xff.split(",")[0].strip()
            if first:
                return first
        real = request.headers.get("x-real-ip")
        if real:
            return real.strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
