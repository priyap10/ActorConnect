"""Security middleware: response headers and rate limiting."""
import logging
import re

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

logger = logging.getLogger(__name__)

CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data: blob:",
        "media-src 'self' blob:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"


class SecurityHeadersMiddleware:
    """Adds a strict Content-Security-Policy and other hardening headers.

    The Django admin is excluded from the CSP because it ships a few inline
    snippets; it is protected by login, staff permissions and a configurable URL.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        admin_prefix = "/" + settings.ADMIN_URL.lstrip("/")
        if not request.path.startswith(admin_prefix):
            response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)

        content_type = response.headers.get("Content-Type", "")
        if (
            request.user.is_authenticated
            and content_type.startswith("text/html")
            and "Cache-Control" not in response.headers
        ):
            response.headers["Cache-Control"] = "private, no-store"
        return response


class RateLimitMiddleware:
    """Fixed-window rate limiting by client IP, driven by settings.RATE_LIMITS."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.rules = [
            {**rule, "regex": re.compile("^" + re.escape(rule["prefix"]))}
            for rule in getattr(settings, "RATE_LIMITS", [])
        ]

    def __call__(self, request):
        ip = self._client_ip(request)
        for rule in self.rules:
            if request.method not in rule["methods"] or not rule["regex"].match(request.path):
                continue
            if self._exceeded(rule, ip):
                logger.warning("Rate limit '%s' exceeded by %s", rule["name"], ip)
                response = HttpResponse(
                    "Too many requests. Please wait a moment and try again.",
                    status=429,
                    content_type="text/plain; charset=utf-8",
                )
                response.headers["Retry-After"] = str(rule["window"])
                return response
        return self.get_response(request)

    @staticmethod
    def _exceeded(rule, ip):
        key = f"rl:{rule['name']}:{ip}"
        cache.add(key, 0, rule["window"])
        try:
            count = cache.incr(key)
        except ValueError:  
            cache.set(key, 1, rule["window"])
            count = 1
        return count > rule["limit"]

    @staticmethod
    def _client_ip(request):
        if settings.RATE_LIMIT_TRUST_XFF:
            forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")