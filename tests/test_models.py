"""Tests for data models."""

from datetime import datetime

from pytest_api_coverage.models import HTTPRequest, HTTPResponse


def test_http_request_creation():
    """Test HTTPRequest dataclass creation."""
    req = HTTPRequest(
        method="GET",
        url="https://api.example.com/users",
        path="/users",
        host="api.example.com",
    )
    assert req.method == "GET"
    assert req.path == "/users"
    assert req.headers == {}
    assert req.query_params == {}


def test_http_request_with_all_fields():
    """Test HTTPRequest with all fields."""
    req = HTTPRequest(
        method="POST",
        url="https://api.example.com/users",
        path="/users",
        host="api.example.com",
        headers={"Content-Type": "application/json"},
        query_params={"page": ["1"]},
        body={"name": "test"},
        content_type="application/json",
    )
    assert req.headers == {"Content-Type": "application/json"}
    assert req.body == {"name": "test"}


def test_http_response_creation():
    """Test HTTPResponse dataclass creation."""
    resp = HTTPResponse(status_code=200)
    assert resp.status_code == 200
    assert resp.headers == {}
    assert resp.body_size == 0


def test_http_interaction_creation(make_interaction):
    """Test HTTPInteraction dataclass creation."""
    interaction = make_interaction()

    assert interaction.request.method == "GET"
    assert interaction.response.status_code == 200
    assert interaction.test_name is None
    assert interaction.duration_ms == 0.0
    assert isinstance(interaction.timestamp, datetime)


def test_http_interaction_with_test_name(make_interaction):
    """Test HTTPInteraction with test name."""
    interaction = make_interaction(
        test_name="test_example",
        duration_ms=123.45,
    )

    assert interaction.test_name == "test_example"
    assert interaction.duration_ms == 123.45
