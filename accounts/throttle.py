"""
Simple IP-based rate limiting using Django's cache framework.
No additional packages required; works with the default in-memory cache for
local development and a shared cache in deployment.

Usage:
    allowed = check_throttle(request, "login", limit=10, window=300)
    if not allowed:
        # return 429-style response
"""

from django.core.cache import cache


def _client_ip(request):
    """Return the best-guess client IP; prefers X-Forwarded-For in hosted environments."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def check_throttle(request, action: str, limit: int = 10, window: int = 300) -> bool:
    """
    Return True if the request is allowed, False if rate-limited.

    Uses a simple counter keyed by (action, IP address).
    Each call increments the counter; the counter expires after *window* seconds.
    Default: 10 attempts per 5 minutes.

    Note: the counter resets on expiry, not on a strict sliding window.
    This is intentional: it avoids complexity for a simple brute-force deterrent.
    """
    ip = _client_ip(request)
    key = f"throttle:{action}:{ip}"
    count = cache.get(key, 0)
    if count >= limit:
        return False
    cache.set(key, count + 1, timeout=window)
    return True
