"""Shared HTTP rate limiter for public website endpoints."""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address


def rate_limit_key(request):
    """Return the client address used by the limiter.

    Forwarded client headers are intentionally not trusted here. If the service
    is deployed behind a proxy, configure the proxy to preserve the real client
    address and replace this function only after that trust boundary is defined.
    """
    return get_remote_address(request)


storage_uri = os.getenv("WAQD_RATE_LIMIT_STORAGE_URI", "").strip()

limiter = Limiter(
    key_func=rate_limit_key,
    # This hobby deployment should remain usable when Redis is intentionally
    # omitted or temporarily unavailable. SlowAPI then fails open; the limits
    # are protection, not an authentication or authorization control.
    storage_uri=storage_uri or None,
    enabled=bool(storage_uri),
    swallow_errors=True,
)
