"""
Error helpers — separate user-facing error messages from internal logs.

A common mistake in API code is to return str(exc) directly in the
response body. That leaks file paths, library versions, SQL
fragments, stack trace text — all useful to an attacker. Instead,
log the full exception (with traceback) on the server, and return
a short, generic message to the client.

In development we still want to see the detail in the response so
we can debug without tailing logs. The rule: in DEBUG mode, include
the original str(exc); in production, replace it with a generic
phrase + a server-side correlation id the user can quote to
support.
"""
from __future__ import annotations

import logging
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)


def safe_error_response(
    exc: Exception,
    *,
    user_message: str,
    context: str = "",
    log_level: int = logging.ERROR,
) -> tuple[str, str | None]:
    """
    Returns (client_message, correlation_id).

    client_message — what to put in the JSON response.
    correlation_id — short id the user can quote when reporting the
        error; matches the log line so support can find it.

    In DEBUG: client_message is the original str(exc).
    In production: client_message is `user_message` ("Operation
    failed", "Could not load symbol data", etc.) and the
    correlation_id ties it to the server-side log.
    """
    correlation_id = uuid.uuid4().hex[:12]
    if settings.DEBUG:
        client_msg = f"{user_message}: {exc}"
    else:
        client_msg = user_message
    logger.log(
        log_level,
        "api error corr_id=%s context=%s exc_type=%s exc=%s",
        correlation_id,
        context,
        type(exc).__name__,
        exc,
        exc_info=log_level >= logging.ERROR,
    )
    return client_msg, correlation_id
