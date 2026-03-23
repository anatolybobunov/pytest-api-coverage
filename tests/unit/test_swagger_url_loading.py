"""Unit tests for SwaggerParser URL loading via mocked HTTP."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pytest_api_coverage.schemas.swagger import SwaggerParser  # noqa: E402

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

    def test_parse_raises_when_httpx_unavailable(self) -> None:
        """SwaggerParser.parse raises ImportError when httpx is not installed."""
        with patch("pytest_api_coverage.schemas.swagger.httpx", None):
            with pytest.raises(ImportError, match="httpx"):
                SwaggerParser.parse("https://example.com/openapi.json")
