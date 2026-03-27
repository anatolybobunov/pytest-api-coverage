"""Unit tests for SwaggerParser URL loading via mocked HTTP."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pytest_api_coverage.schemas.swagger import SwaggerParser, format_spec_load_error  # noqa: E402

MINIMAL_OPENAPI_JSON = """{
  "openapi": "3.0.0",
  "info": {"title": "Test", "version": "1.0"},
  "paths": {
    "/users": {
      "get": {"responses": {"200": {"description": "OK"}}}
    }
  }
}"""

MINIMAL_OPENAPI_YAML = """\
openapi: "3.0.0"
info:
  title: Test
  version: "1.0"
paths:
  /users:
    get:
      responses:
        "200":
          description: OK
"""


def _make_mock_response(text: str, content_type: str = "application/json") -> MagicMock:
    """Build a minimal httpx.Response mock."""
    mock_resp = MagicMock()
    mock_resp.text = text
    mock_resp.headers = {"content-type": content_type}
    mock_resp.json.return_value = __import__("json").loads(text) if "json" in content_type else {}
    mock_resp.raise_for_status.return_value = None
    return mock_resp


class TestSwaggerParserUrlLoading:
    def test_parse_json_from_url(self) -> None:
        """SwaggerParser.parse fetches JSON spec from an HTTP URL."""
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: s
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = _make_mock_response(MINIMAL_OPENAPI_JSON, "application/json")

        with patch("pytest_api_coverage.schemas.swagger.httpx") as mock_httpx:
            mock_httpx.Client.return_value = mock_client

            spec = SwaggerParser.parse("https://example.com/openapi.json")

        assert spec is not None
        assert any(e.path == "/users" and e.method == "GET" for e in spec.endpoints)

    def test_parse_yaml_from_url_by_content_type(self) -> None:
        """SwaggerParser.parse handles YAML content type in response."""
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: s
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = _make_mock_response(MINIMAL_OPENAPI_YAML, "application/yaml")

        with patch("pytest_api_coverage.schemas.swagger.httpx") as mock_httpx:
            mock_httpx.Client.return_value = mock_client

            spec = SwaggerParser.parse("https://example.com/openapi")

        assert spec is not None
        assert any(e.path == "/users" and e.method == "GET" for e in spec.endpoints)

    def test_parse_yaml_from_url_by_extension(self) -> None:
        """SwaggerParser.parse detects YAML from .yaml extension when content-type is generic."""
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: s
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = _make_mock_response(MINIMAL_OPENAPI_YAML, "text/plain")

        with patch("pytest_api_coverage.schemas.swagger.httpx") as mock_httpx:
            mock_httpx.Client.return_value = mock_client

            spec = SwaggerParser.parse("https://example.com/openapi.yaml")

        assert spec is not None
        assert any(e.path == "/users" for e in spec.endpoints)

    def test_parse_raises_on_http_error(self) -> None:
        """SwaggerParser.parse propagates HTTP errors from the remote server."""
        import httpx as real_httpx

        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: s
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = real_httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(),
        )
        mock_client.get.return_value = mock_response

        with patch("pytest_api_coverage.schemas.swagger.httpx") as mock_httpx:
            mock_httpx.Client.return_value = mock_client
            mock_httpx.HTTPStatusError = real_httpx.HTTPStatusError

            with pytest.raises(real_httpx.HTTPStatusError):
                SwaggerParser.parse("https://example.com/missing.json")

    def test_parse_raises_when_both_unavailable(self) -> None:
        """SwaggerParser.parse raises ImportError when neither httpx nor requests is installed."""
        with patch("pytest_api_coverage.schemas.swagger.httpx", None):
            with patch("pytest_api_coverage.schemas.swagger.requests_lib", None):
                with pytest.raises(ImportError, match="httpx"):
                    SwaggerParser.parse("https://example.com/openapi.json")

    def test_parse_json_from_url_requests_fallback(self) -> None:
        """SwaggerParser.parse uses requests when httpx is not installed."""
        mock_response = _make_mock_response(MINIMAL_OPENAPI_JSON, "application/json")
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("pytest_api_coverage.schemas.swagger.httpx", None):
            with patch("pytest_api_coverage.schemas.swagger.requests_lib", mock_requests):
                spec = SwaggerParser.parse("https://example.com/openapi.json")

        assert spec is not None
        assert any(e.path == "/users" and e.method == "GET" for e in spec.endpoints)
        mock_requests.get.assert_called_once_with(
            "https://example.com/openapi.json", timeout=SwaggerParser.REQUEST_TIMEOUT
        )

    def test_parse_yaml_from_url_requests_fallback(self) -> None:
        """SwaggerParser.parse uses requests to load a YAML spec when httpx is absent."""
        mock_response = _make_mock_response(MINIMAL_OPENAPI_YAML, "application/yaml")
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("pytest_api_coverage.schemas.swagger.httpx", None):
            with patch("pytest_api_coverage.schemas.swagger.requests_lib", mock_requests):
                spec = SwaggerParser.parse("https://example.com/openapi.yaml")

        assert spec is not None
        assert any(e.path == "/users" and e.method == "GET" for e in spec.endpoints)

    def test_parse_prefers_httpx_over_requests(self) -> None:
        """When both httpx and requests are available, httpx is used."""
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: s
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = _make_mock_response(MINIMAL_OPENAPI_JSON, "application/json")

        mock_requests = MagicMock()

        with patch("pytest_api_coverage.schemas.swagger.httpx") as mock_httpx:
            mock_httpx.Client.return_value = mock_client
            with patch("pytest_api_coverage.schemas.swagger.requests_lib", mock_requests):
                SwaggerParser.parse("https://example.com/openapi.json")

        mock_requests.get.assert_not_called()


class TestFormatSpecLoadErrorRequests:
    def test_http_error_with_response(self) -> None:
        """format_spec_load_error formats requests.HTTPError with status code."""
        import requests as real_requests

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.reason = "Not Found"
        err = real_requests.exceptions.HTTPError(response=mock_response)

        result = format_spec_load_error(err)
        assert "404" in result
        assert "Not Found" in result

    def test_http_error_redirect(self) -> None:
        """format_spec_load_error returns redirect hint for 3xx responses."""
        import requests as real_requests

        mock_response = MagicMock()
        mock_response.status_code = 301
        mock_response.reason = "Moved Permanently"
        mock_response.headers = {"location": "https://new.example.com/api.json"}
        err = real_requests.exceptions.HTTPError(response=mock_response)

        result = format_spec_load_error(err)
        assert "301" in result
        assert "redirect" in result

    def test_timeout_error(self) -> None:
        """format_spec_load_error returns timeout message for requests.Timeout."""
        import requests as real_requests

        err = real_requests.exceptions.Timeout("timed out")
        result = format_spec_load_error(err)
        assert "timed out" in result.lower()

    def test_connection_error(self) -> None:
        """format_spec_load_error returns connection failed for requests.ConnectionError."""
        import requests as real_requests

        err = real_requests.exceptions.ConnectionError("refused")
        result = format_spec_load_error(err)
        assert "Connection failed" in result

    def test_requests_errors_skipped_when_requests_unavailable(self) -> None:
        """format_spec_load_error falls back to str() when requests_lib is None."""
        err = ValueError("some generic error")
        with patch("pytest_api_coverage.schemas.swagger.requests_lib", None):
            result = format_spec_load_error(err)
        assert result == "some generic error"
