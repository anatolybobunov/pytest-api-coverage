"""Shared utility functions for pytest-api-coverage."""

from __future__ import annotations

from urllib.parse import urlparse


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
        parsed = urlparse(f"https://{url}")

    scheme = parsed.scheme or "https"
    host = parsed.hostname or parsed.netloc or url
    port = parsed.port

    # Omit standard ports
    if port and ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        port = None

    if port:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"
