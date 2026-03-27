"""Swagger/OpenAPI specification parser."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

try:
    import requests as requests_lib
except ImportError:
    requests_lib = None  # type: ignore[assignment]

import yaml


@dataclass
class SwaggerParameter:
    """Represents a parameter from swagger spec."""

    name: str
    location: str  # "path", "query", "header", "body", "formData"
    required: bool = False
    param_type: str | None = None  # "string", "integer", etc.
    schema: dict[str, Any] | None = None


@dataclass
class SwaggerResponse:
    """Represents a response definition from swagger spec."""

    status_code: int
    description: str = ""
    schema: dict[str, Any] | None = None


@dataclass
class SwaggerEndpoint:
    """Represents a single API endpoint from swagger spec."""

    method: str  # GET, POST, PUT, DELETE, PATCH, etc.
    path: str  # /users/{id}
    operation_id: str | None = None
    summary: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    parameters: list[SwaggerParameter] = field(default_factory=list)
    responses: list[SwaggerResponse] = field(default_factory=list)
    consumes: list[str] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)


@dataclass
class SwaggerSpec:
    """Complete swagger specification."""

    title: str
    version: str
    base_path: str = ""
    host: str = ""
    schemes: list[str] = field(default_factory=list)
    endpoints: list[SwaggerEndpoint] = field(default_factory=list)
    server_urls: list[str] = field(default_factory=list)  # OpenAPI 3.x servers
    source: str = ""  # Original file path or URL used to load the spec

    def get_endpoint(self, method: str, path: str) -> SwaggerEndpoint | None:
        """Find endpoint by method and path pattern."""
        method = method.upper()
        for endpoint in self.endpoints:
            if endpoint.method.upper() == method and endpoint.path == path:
                return endpoint
        return None


def format_spec_load_error(error: Exception) -> str:
    """Return a concise, human-readable message for a spec load failure.

    Converts verbose httpx/network exceptions into one-line hints without
    exposing the full traceback.  Falls back to ``str(error)`` for unknown
    exception types.
    """
    if httpx is not None:
        if isinstance(error, httpx.HTTPStatusError):
            code = error.response.status_code
            if 300 <= code < 400:
                location = error.response.headers.get("location", "")
                hint = f" → {location}" if location else ""
                return f"HTTP {code} redirect{hint} — spec URL may require authentication"
            reason = error.response.reason_phrase or str(code)
            return f"HTTP {code} {reason}"
        if isinstance(error, httpx.TimeoutException):
            return "Connection timed out while fetching spec"
        if isinstance(error, httpx.ConnectError):
            return f"Connection failed: {error}"
    if requests_lib is not None:
        if isinstance(error, requests_lib.exceptions.HTTPError):
            response = getattr(error, "response", None)
            if response is not None:
                code = response.status_code
                if 300 <= code < 400:
                    location = response.headers.get("location", "")
                    hint = f" → {location}" if location else ""
                    return f"HTTP {code} redirect{hint} — spec URL may require authentication"
                return f"HTTP {code} {response.reason or str(code)}"
        if isinstance(error, requests_lib.exceptions.Timeout):
            return "Connection timed out while fetching spec"
        if isinstance(error, requests_lib.exceptions.ConnectionError):
            return f"Connection failed: {error}"
    return str(error)


class SwaggerParser:
    """Parser for Swagger 2.0 and OpenAPI 3.x specifications.

    Supports:
    - Local file paths (JSON and YAML)
    - Remote URLs (HTTP/HTTPS)
    """

    HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}
    REQUEST_TIMEOUT = 30.0  # seconds

    @classmethod
    def parse(cls, source: str | Path) -> SwaggerSpec:
        """Parse swagger from file path or URL.

        Args:
            source: Local file path or URL to swagger specification

        Returns:
            SwaggerSpec: Parsed specification

        Raises:
            FileNotFoundError: If local file doesn't exist
            httpx.HTTPError: If URL fetch fails
            ValueError: If specification format is invalid
        """
        source_str = str(source)

        if source_str.startswith(("http://", "https://")):
            return cls._parse_from_url(source_str, source_str)
        return cls._parse_from_file(Path(source_str), source_str)

    @classmethod
    def _parse_from_url(cls, url: str, source: str) -> SwaggerSpec:
        """Fetch and parse swagger specification from URL.

        Args:
            url: HTTP/HTTPS URL to swagger specification
            source: Original source string for the report

        Returns:
            SwaggerSpec: Parsed specification
        """
        if httpx is not None:
            with httpx.Client(timeout=cls.REQUEST_TIMEOUT) as client:
                response = client.get(url)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "yaml" in content_type or url.endswith((".yaml", ".yml")):
                    data = yaml.safe_load(response.text)
                else:
                    data = response.json()
        elif requests_lib is not None:
            response = requests_lib.get(url, timeout=cls.REQUEST_TIMEOUT)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "yaml" in content_type or url.endswith((".yaml", ".yml")):
                data = yaml.safe_load(response.text)
            else:
                data = response.json()
        else:
            raise ImportError(
                "A HTTP client is required to fetch remote specs. "
                "Install one: pip install httpx  or  pip install requests"
            )
        return cls._parse_spec(data, source)

    @classmethod
    def _parse_from_file(cls, path: Path, source: str) -> SwaggerSpec:
        """Parse swagger specification from local file.

        Args:
            path: Path to swagger file
            source: Original source string for the report

        Returns:
            SwaggerSpec: Parsed specification
        """
        if not path.exists():
            raise FileNotFoundError(f"Swagger file not found: {path}")

        content = path.read_text(encoding="utf-8")

        if path.suffix.lower() in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)

        return cls._parse_spec(data, source)

    @classmethod
    def _parse_spec(cls, data: dict[str, Any], source: str = "") -> SwaggerSpec:
        """Parse specification dictionary into SwaggerSpec."""
        # Detect OpenAPI version
        if "openapi" in data:
            return cls._parse_openapi3(data, source)
        elif "swagger" in data:
            return cls._parse_swagger2(data, source)
        else:
            source_info = f" in '{source}'" if source else ""
            raise ValueError(f"Unknown specification format{source_info}: missing 'swagger' or 'openapi' key")

    @classmethod
    def _parse_swagger2(cls, data: dict[str, Any], source: str = "") -> SwaggerSpec:
        """Parse Swagger 2.0 specification."""
        info = data.get("info", {})
        spec = SwaggerSpec(
            title=info.get("title", "Unknown API"),
            version=info.get("version", "0.0.0"),
            base_path=data.get("basePath", ""),
            host=data.get("host", ""),
            schemes=data.get("schemes", ["https"]),
            source=source,
        )

        paths = data.get("paths", {})
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in cls.HTTP_METHODS:
                    continue
                if not isinstance(operation, dict):
                    continue

                endpoint = cls._parse_endpoint_swagger2(method, path, operation, data)
                spec.endpoints.append(endpoint)

        return spec

    @classmethod
    def _parse_openapi3(cls, data: dict[str, Any], source: str = "") -> SwaggerSpec:
        """Parse OpenAPI 3.x specification."""
        info = data.get("info", {})
        servers = data.get("servers", [])

        # Extract base_path and host from server URLs
        base_path = ""
        host = ""
        server_urls: list[str] = []

        for server in servers:
            if isinstance(server, dict):
                server_url = server.get("url", "")
                if server_url:
                    server_urls.append(server_url)

        # Use first server for base_path extraction
        if server_urls:
            first_server = server_urls[0]
            parsed = urlparse(first_server)

            if parsed.scheme:
                # Full URL: https://api.example.com/v1
                host = f"{parsed.scheme}://{parsed.netloc}"
                base_path = parsed.path.rstrip("/") or ""
            else:
                # Relative URL: /v1 or /api/v1
                base_path = first_server.rstrip("/") or ""

        spec = SwaggerSpec(
            title=info.get("title", "Unknown API"),
            version=info.get("version", "0.0.0"),
            base_path=base_path,
            host=host,
            server_urls=server_urls,
            source=source,
        )

        paths = data.get("paths", {})
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in cls.HTTP_METHODS:
                    continue
                if not isinstance(operation, dict):
                    continue

                endpoint = cls._parse_endpoint_openapi3(method, path, operation)
                spec.endpoints.append(endpoint)

        return spec

    @classmethod
    def _parse_endpoint_swagger2(
        cls, method: str, path: str, operation: dict[str, Any], spec_data: dict[str, Any]
    ) -> SwaggerEndpoint:
        """Parse single endpoint from Swagger 2.0."""
        parameters = []
        for param in operation.get("parameters", []):
            if not isinstance(param, dict):
                continue
            parameters.append(
                SwaggerParameter(
                    name=param.get("name", ""),
                    location=param.get("in", "query"),
                    required=param.get("required", False),
                    param_type=param.get("type"),
                    schema=param.get("schema"),
                )
            )

        responses = []
        for code, response in operation.get("responses", {}).items():
            try:
                status_code = int(code)
            except ValueError:
                continue  # Skip 'default' or other non-numeric keys
            if not isinstance(response, dict):
                continue
            responses.append(
                SwaggerResponse(
                    status_code=status_code,
                    description=response.get("description", ""),
                    schema=response.get("schema"),
                )
            )

        return SwaggerEndpoint(
            method=method.upper(),
            path=path,
            operation_id=operation.get("operationId"),
            summary=operation.get("summary"),
            description=operation.get("description"),
            tags=operation.get("tags", []),
            parameters=parameters,
            responses=responses,
            consumes=operation.get("consumes", spec_data.get("consumes", [])),
            produces=operation.get("produces", spec_data.get("produces", [])),
        )

    @classmethod
    def _parse_endpoint_openapi3(cls, method: str, path: str, operation: dict[str, Any]) -> SwaggerEndpoint:
        """Parse single endpoint from OpenAPI 3.x."""
        parameters = []
        for param in operation.get("parameters", []):
            if not isinstance(param, dict):
                continue
            parameters.append(
                SwaggerParameter(
                    name=param.get("name", ""),
                    location=param.get("in", "query"),
                    required=param.get("required", False),
                    schema=param.get("schema"),
                )
            )

        # Handle requestBody (OpenAPI 3.x)
        request_body = operation.get("requestBody", {})
        if request_body and isinstance(request_body, dict):
            content = request_body.get("content", {})
            for _content_type, media_type in content.items():
                if isinstance(media_type, dict):
                    parameters.append(
                        SwaggerParameter(
                            name="body",
                            location="body",
                            required=request_body.get("required", False),
                            schema=media_type.get("schema"),
                        )
                    )
                break  # Only add first content type

        responses = []
        for code, response in operation.get("responses", {}).items():
            try:
                status_code = int(code)
            except ValueError:
                continue  # Skip 'default' or other non-numeric keys
            if not isinstance(response, dict):
                continue
            responses.append(
                SwaggerResponse(
                    status_code=status_code,
                    description=response.get("description", ""),
                )
            )

        return SwaggerEndpoint(
            method=method.upper(),
            path=path,
            operation_id=operation.get("operationId"),
            summary=operation.get("summary"),
            description=operation.get("description"),
            tags=operation.get("tags", []),
            parameters=parameters,
            responses=responses,
        )
