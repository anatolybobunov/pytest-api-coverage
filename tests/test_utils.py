"""Tests for shared utility functions."""
import pytest
from pytest_api_coverage.utils import normalize_origin


@pytest.mark.parametrize("url, expected", [
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
    # No scheme - defaults to https
    ("api.example.com", "https://api.example.com"),
    # Already-normalized origin
    ("https://api.example.com:9000", "https://api.example.com:9000"),
])
def test_normalize_origin(url, expected):
    assert normalize_origin(url) == expected
