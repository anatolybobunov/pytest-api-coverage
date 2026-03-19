"""Tests for shared utility functions."""

import pytest

from pytest_api_coverage.utils import normalize_origin, url_matches_filter


@pytest.mark.parametrize(
    "url, expected",
    [
        # Standard https - port omitted
        ("https://api.example.com", "https://api.example.com"),
        ("https://api.example.com:443", "https://api.example.com"),
        ("https://api.example.com:443/path/here", "https://api.example.com"),
        # Standard http - port omitted
        ("http://api.example.com", "http://api.example.com"),
        ("http://api.example.com:80", "http://api.example.com"),
        # Non-standard port - kept
        ("https://api.example.com:8443", "https://api.example.com:8443"),
        ("http://localhost:8080", "http://localhost:8080"),
        # No scheme - defaults to http
        ("api.example.com", "http://api.example.com"),
        # Already-normalized origin
        ("https://api.example.com:9000", "https://api.example.com:9000"),
    ],
)
def test_normalize_origin(url, expected):
    assert normalize_origin(url) == expected


@pytest.mark.parametrize(
    "request_url, filter_value, expected",
    [
        # Full URL filter matches exact origin
        ("https://api.example.com/users", "https://api.example.com", True),
        # Hostname without scheme matches https request
        ("https://authdb-test.exante.eu/api/v1", "authdb-test.exante.eu", True),
        # Hostname without scheme matches http request
        ("http://authdb-test.exante.eu/api/v1", "authdb-test.exante.eu", True),
        # Partial hostname matches
        ("https://authdb-test.exante.eu/api/v1", "authdb-test", True),
        # Case-insensitive match
        ("https://API.EXAMPLE.COM/users", "api.example.com", True),
        ("https://api.example.com/users", "API.EXAMPLE.COM", True),
        # Non-matching filter returns False
        ("https://api.example.com/users", "other.example.com", False),
        # Filter with path matches URL containing that path
        ("https://api.example.com/auth/login", "https://api.example.com/auth", True),
        # Scheme mismatch is handled by substring: https:// filter won't match http://
        ("http://api.example.com/users", "https://api.example.com", False),
    ],
)
def test_url_matches_filter(request_url, filter_value, expected):
    assert url_matches_filter(request_url, filter_value) == expected
