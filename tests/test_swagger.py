"""Tests for SwaggerParser."""

from pathlib import Path

import pytest

from pytest_api_coverage.schemas import SwaggerSpec
from pytest_api_coverage.schemas.swagger import SwaggerEndpoint, SwaggerParser


def test_parse_swagger2_from_file(temp_swagger_file: Path):
    """Test parsing Swagger 2.0 from file."""
    spec = SwaggerParser.parse(temp_swagger_file)

    assert spec.title == "Test API"
    assert spec.version == "1.0.0"
    assert spec.base_path == "/api/v1"
    assert len(spec.endpoints) == 4


def test_parse_swagger2_endpoints(temp_swagger_file: Path):
    """Test that endpoints are correctly parsed."""
    spec = SwaggerParser.parse(temp_swagger_file)

    # Check GET /users endpoint
    endpoint = spec.get_endpoint("GET", "/users")
    assert endpoint is not None
    assert endpoint.method == "GET"
    assert endpoint.path == "/users"
    assert endpoint.summary == "List users"

    # Check POST /users endpoint
    endpoint = spec.get_endpoint("POST", "/users")
    assert endpoint is not None
    assert endpoint.summary == "Create user"

    # Check GET /users/{id}
    endpoint = spec.get_endpoint("GET", "/users/{id}")
    assert endpoint is not None
    assert len(endpoint.responses) == 2  # 200 and 404

    # Check DELETE /users/{id}
    endpoint = spec.get_endpoint("DELETE", "/users/{id}")
    assert endpoint is not None


def test_parse_swagger2_responses(temp_swagger_file: Path):
    """Test that responses are correctly parsed."""
    spec = SwaggerParser.parse(temp_swagger_file)
    endpoint = spec.get_endpoint("GET", "/users/{id}")

    assert len(endpoint.responses) == 2
    status_codes = {r.status_code for r in endpoint.responses}
    assert status_codes == {200, 404}


def test_parse_openapi3(parse_swagger):
    """Test parsing OpenAPI 3.0 specification."""
    spec = parse_swagger(
        {
            "openapi": "3.0.0",
            "info": {"title": "OpenAPI 3 Test", "version": "2.0.0"},
            "servers": [{"url": "/api/v2"}],
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "listItems",
                        "summary": "List items",
                        "responses": {"200": {"description": "OK"}},
                    },
                    "post": {
                        "operationId": "createItem",
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        },
                        "responses": {"201": {"description": "Created"}},
                    },
                }
            },
        }
    )

    assert spec.title == "OpenAPI 3 Test"
    assert spec.version == "2.0.0"
    assert spec.base_path == "/api/v2"
    assert len(spec.endpoints) == 2

    # Check GET endpoint
    get_endpoint = spec.get_endpoint("GET", "/items")
    assert get_endpoint is not None
    assert get_endpoint.operation_id == "listItems"

    # Check POST endpoint with requestBody
    post_endpoint = spec.get_endpoint("POST", "/items")
    assert post_endpoint is not None
    assert post_endpoint.operation_id == "createItem"
    # Should have body parameter from requestBody
    body_params = [p for p in post_endpoint.parameters if p.location == "body"]
    assert len(body_params) == 1
    assert body_params[0].required is True


def test_parse_yaml_file(parse_swagger):
    """Test parsing YAML swagger file."""
    spec = parse_swagger(
        {
            "swagger": "2.0",
            "info": {"title": "YAML API", "version": "1.0.0"},
            "basePath": "/yaml",
            "paths": {"/test": {"get": {"summary": "Test endpoint", "responses": {"200": {"description": "OK"}}}}},
        },
        filename="swagger.yaml",
    )

    assert spec.title == "YAML API"
    assert spec.base_path == "/yaml"
    assert len(spec.endpoints) == 1


def test_parse_file_not_found():
    """Test error handling for missing file."""
    with pytest.raises(FileNotFoundError):
        SwaggerParser.parse("/nonexistent/path/swagger.json")


def test_parse_invalid_format(parse_swagger):
    """Test error handling for invalid specification."""
    with pytest.raises(ValueError, match="Unknown specification format"):
        parse_swagger({"invalid": "spec"})


def test_swagger_spec_get_endpoint():
    """Test SwaggerSpec.get_endpoint method."""
    spec = SwaggerSpec(
        title="Test",
        version="1.0",
        endpoints=[
            SwaggerEndpoint(method="GET", path="/users"),
            SwaggerEndpoint(method="POST", path="/users"),
            SwaggerEndpoint(method="GET", path="/users/{id}"),
        ],
    )

    # Test exact match
    assert spec.get_endpoint("GET", "/users") is not None
    assert spec.get_endpoint("get", "/users") is not None  # Case insensitive
    assert spec.get_endpoint("POST", "/users") is not None

    # Test not found
    assert spec.get_endpoint("DELETE", "/users") is None
    assert spec.get_endpoint("GET", "/nonexistent") is None


def test_parse_parameters(parse_swagger):
    """Test parameter parsing from Swagger 2.0."""
    spec = parse_swagger(
        {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/users/{id}": {
                    "get": {
                        "parameters": [
                            {"name": "id", "in": "path", "required": True, "type": "integer"},
                            {"name": "include", "in": "query", "type": "string"},
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
    )
    endpoint = spec.get_endpoint("GET", "/users/{id}")

    assert len(endpoint.parameters) == 2

    path_param = next(p for p in endpoint.parameters if p.name == "id")
    assert path_param.location == "path"
    assert path_param.required is True
    assert path_param.param_type == "integer"

    query_param = next(p for p in endpoint.parameters if p.name == "include")
    assert query_param.location == "query"
    assert query_param.required is False


def test_parse_tags_and_metadata(parse_swagger):
    """Test parsing of tags and metadata."""
    spec = parse_swagger(
        {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "summary": "List all users",
                        "description": "Returns a list of users",
                        "tags": ["users", "admin"],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
    )
    endpoint = spec.get_endpoint("GET", "/users")

    assert endpoint.operation_id == "listUsers"
    assert endpoint.summary == "List all users"
    assert endpoint.description == "Returns a list of users"
    assert endpoint.tags == ["users", "admin"]


def test_parse_openapi3_full_url_servers(parse_swagger):
    """Test OpenAPI 3.x with full URL in servers extracts base_path correctly."""
    spec = parse_swagger(
        {
            "openapi": "3.0.0",
            "info": {"title": "Full URL API", "version": "1.0.0"},
            "servers": [
                {"url": "https://api.example.com/v1"},
                {"url": "https://staging.example.com/v1"},
            ],
            "paths": {
                "/users": {
                    "get": {
                        "summary": "List users",
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
    )

    # base_path should be extracted from full URL
    assert spec.base_path == "/v1"
    assert spec.host == "https://api.example.com"

    # All server URLs should be stored
    assert len(spec.server_urls) == 2
    assert "https://api.example.com/v1" in spec.server_urls
    assert "https://staging.example.com/v1" in spec.server_urls


def test_parse_openapi3_server_with_deep_path(parse_swagger):
    """Test OpenAPI 3.x server URL with deep path prefix."""
    spec = parse_swagger(
        {
            "openapi": "3.0.0",
            "info": {"title": "Deep Path API", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com/api/v2/service"}],
            "paths": {"/items": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }
    )

    assert spec.base_path == "/api/v2/service"
    assert spec.host == "https://api.example.com"


def test_parse_openapi3_server_no_path(parse_swagger):
    """Test OpenAPI 3.x server URL without path prefix."""
    spec = parse_swagger(
        {
            "openapi": "3.0.0",
            "info": {"title": "No Path API", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com"}],
            "paths": {"/items": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }
    )

    assert spec.base_path == ""
    assert spec.host == "https://api.example.com"


def test_parse_openapi3_no_servers(parse_swagger):
    """Test OpenAPI 3.x without servers section."""
    spec = parse_swagger(
        {
            "openapi": "3.0.0",
            "info": {"title": "No Servers API", "version": "1.0.0"},
            "paths": {"/items": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }
    )

    assert spec.base_path == ""
    assert spec.host == ""
    assert spec.server_urls == []
