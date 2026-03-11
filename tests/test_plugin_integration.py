"""Integration test for pytest plugin."""

import requests
import responses


@responses.activate
def test_http_request_is_captured():
    """Test that HTTP requests are captured by the plugin."""
    responses.add(
        responses.GET,
        "https://httpbin.org/get",
        json={"args": {"test": "value"}},
        status=200,
    )

    response = requests.get("https://httpbin.org/get", params={"test": "value"})

    assert response.status_code == 200
    assert response.json()["args"]["test"] == "value"


@responses.activate
def test_post_request_with_json():
    """Test POST request with JSON body."""
    responses.add(
        responses.POST,
        "https://httpbin.org/post",
        json={"json": {"name": "pytest", "value": 123}},
        status=200,
    )

    response = requests.post(
        "https://httpbin.org/post",
        json={"name": "pytest", "value": 123},
    )

    assert response.status_code == 200
    assert response.json()["json"]["name"] == "pytest"
