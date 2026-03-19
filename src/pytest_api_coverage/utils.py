"""Shared utility functions for pytest-api-coverage."""

from __future__ import annotations

from urllib.parse import urlparse


def matches_filter_value(request_url: str, filter_value: str) -> bool:
    """Check if request_url matches a spec filter value (origin + path prefix).

    Handles both bare hostnames and full URLs with optional path prefix.
    Trailing-slash safe: ``/auth`` matches ``/auth/users`` but NOT ``/authentic``.

    Args:
        request_url: Full URL of the HTTP request.
        filter_value: Spec filter — a hostname, origin, or URL with optional path prefix.

    Returns:
        True if request_url belongs to the origin and path defined by filter_value.
    """
    parsed_req = urlparse(request_url)
    parsed_filter = urlparse(
        filter_value if filter_value.startswith(("http://", "https://")) else f"http://{filter_value}"
    )

    # Determine the origin part for the initial coarse filter
    if "://" in filter_value:
        spec_origin = f"{parsed_filter.scheme}://{parsed_filter.netloc}"
    else:
        spec_origin = filter_value.split("/")[0]  # bare hostname without path

    if not url_matches_filter(request_url, spec_origin):
        return False

    spec_path = parsed_filter.path or "/"
    req_path = parsed_req.path or "/"

    # Trailing-slash-safe prefix check: /auth must match /auth/users but NOT /authentic
    normalized_spec = spec_path.rstrip("/")
    return req_path == spec_path or req_path.startswith(normalized_spec + "/")


def url_matches_filter(request_url: str, filter_value: str) -> bool:
    """Check if filter_value is a substring of request_url (case-insensitive).

    Args:
        request_url: Full URL of the HTTP request
        filter_value: Filter string to search for (hostname, origin, or partial URL)

    Returns:
        True if filter_value is found anywhere in request_url
    """
    return filter_value.lower() in request_url.lower()


def normalize_origin(url: str) -> str:
    """Extract and normalize origin from URL (scheme://host[:port]).

    Standard ports (80 for http, 443 for https) are omitted.

    Args:
        url: Full URL or bare host

    Returns:
        Normalized origin string like 'https://api.example.com'
    """
    parsed = urlparse(url)

    # Handle bare hostname without scheme
    if not parsed.scheme:
        parsed = urlparse(f"http://{url}")

    scheme = parsed.scheme or "http"
    host = parsed.hostname or parsed.netloc or url
    port = parsed.port

    # Omit standard ports
    if port and ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        port = None

    if port:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"
