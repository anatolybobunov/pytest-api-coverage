"""Pytest configuration and fixtures for tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pytest_api_coverage.models import HTTPInteraction, HTTPRequest, HTTPResponse
from pytest_api_coverage.reporter import CoverageReporter
from pytest_api_coverage.schemas import SwaggerSpec
from pytest_api_coverage.schemas.swagger import SwaggerEndpoint, SwaggerParser


@pytest.fixture
def temp_swagger_file(tmp_path: Path) -> Path:
    """Create a temporary swagger file for testing."""
    swagger_data = {
        "swagger": "2.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "basePath": "/api/v1",
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "summary": "Create user",
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/users/{id}": {
                "get": {
                    "summary": "Get user",
                    "responses": {"200": {"description": "OK"}, "404": {"description": "Not found"}},
                },
                "delete": {
                    "summary": "Delete user",
                    "responses": {"204": {"description": "Deleted"}},
                },
            },
        },
    }

    path = tmp_path / "swagger.json"
    path.write_text(json.dumps(swagger_data, indent=2))
    return path


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test output."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def simple_swagger_spec() -> SwaggerSpec:
    """Create a simple swagger spec for testing.

    Contains 4 endpoints:
    - GET /users
    - POST /users
    - GET /users/{id}
    - DELETE /users/{id}
    """
    return SwaggerSpec(
        title="Test API",
        version="1.0.0",
        base_path="/api/v1",
        endpoints=[
            SwaggerEndpoint(method="GET", path="/users"),
            SwaggerEndpoint(method="POST", path="/users"),
            SwaggerEndpoint(method="GET", path="/users/{id}"),
            SwaggerEndpoint(method="DELETE", path="/users/{id}"),
        ],
    )


@pytest.fixture
def interactions_multi_origin() -> list[dict]:
    """Interactions from multiple origins for testing.

    Contains interactions from:
    - api.example.com (2 requests)
    - proxy.example.com (2 requests)
    - other.service.com (1 request)

    Note: test_split_by_origin.py has its own fixture with different data.
    """
    return [
        # From api.example.com
        {
            "request": {
                "method": "GET",
                "url": "https://api.example.com/api/v1/users",
                "path": "/api/v1/users",
            },
            "response": {"status_code": 200},
            "test_name": "test_api_users",
        },
        {
            "request": {
                "method": "POST",
                "url": "https://api.example.com/api/v1/users",
                "path": "/api/v1/users",
            },
            "response": {"status_code": 201},
            "test_name": "test_api_create_user",
        },
        # From proxy.example.com (same paths, different origin)
        {
            "request": {
                "method": "GET",
                "url": "https://proxy.example.com/api/v1/users",
                "path": "/api/v1/users",
            },
            "response": {"status_code": 200},
            "test_name": "test_proxy_users",
        },
        {
            "request": {
                "method": "GET",
                "url": "https://proxy.example.com/api/v1/users/123",
                "path": "/api/v1/users/123",
            },
            "response": {"status_code": 200},
            "test_name": "test_proxy_user_detail",
        },
        # From other.service.com (should be filtered out when base_url is set)
        {
            "request": {
                "method": "GET",
                "url": "https://other.service.com/api/v1/users",
                "path": "/api/v1/users",
            },
            "response": {"status_code": 200},
            "test_name": "test_other_service",
        },
    ]


# ============== FACTORY FIXTURES ==============


@pytest.fixture
def make_interaction():
    """Factory for creating HTTP interactions.

    Usage:
        interaction = make_interaction(method="POST", path="/items", status_code=201)
        interaction = make_interaction()  # defaults: GET /users 200
    """

    def _make(
        method: str = "GET",
        path: str = "/users",
        status_code: int = 200,
        host: str = "test.com",
        url: str | None = None,
        headers: dict | None = None,
        query_params: dict | None = None,
        body: Any = None,
        test_name: str | None = None,
        duration_ms: float = 0.0,
        response_headers: dict | None = None,
    ) -> HTTPInteraction:
        if url is None:
            url = f"http://{host}{path}"

        req = HTTPRequest(
            method=method,
            url=url,
            path=path,
            host=host,
            headers=headers or {},
            query_params=query_params or {},
            body=body,
        )
        resp = HTTPResponse(
            status_code=status_code,
            headers=response_headers or {},
        )
        return HTTPInteraction(
            request=req,
            response=resp,
            test_name=test_name,
            duration_ms=duration_ms,
        )

    return _make


@pytest.fixture
def make_swagger_spec():
    """Factory for creating SwaggerSpec with custom endpoints.

    Usage:
        spec = make_swagger_spec(endpoints=[("GET", "/users"), ("POST", "/users")])
        spec = make_swagger_spec(base_path="/v2")
    """

    def _make(
        endpoints: list[tuple[str, str]] | None = None,
        base_path: str = "/api/v1",
        title: str = "Test API",
        version: str = "1.0.0",
    ) -> SwaggerSpec:
        if endpoints is None:
            endpoints = [("GET", "/users")]

        return SwaggerSpec(
            title=title,
            version=version,
            base_path=base_path,
            endpoints=[SwaggerEndpoint(method=m, path=p) for m, p in endpoints],
        )

    return _make


@pytest.fixture
def make_coverage_report():
    """Factory for generating coverage reports.

    Usage:
        report = make_coverage_report(swagger_spec, interactions)
        report = make_coverage_report(swagger_spec, interactions, split_by_origin=True)
    """

    def _make(
        swagger_spec: SwaggerSpec,
        interactions: list[dict],
        **kwargs: Any,
    ) -> dict:
        reporter = CoverageReporter(swagger_spec, **kwargs)
        reporter.process_interactions(interactions)
        return reporter.generate_report()

    return _make


@pytest.fixture
def parse_swagger(tmp_path: Path):
    """Parse swagger data from dict via temporary file.

    Usage:
        spec = parse_swagger({"openapi": "3.0.0", ...})
        spec = parse_swagger(data, filename="swagger.yaml")
    """

    def _parse(data: dict, filename: str = "swagger.json") -> SwaggerSpec:
        spec_file = tmp_path / filename
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            import yaml

            spec_file.write_text(yaml.dump(data))
        else:
            spec_file.write_text(json.dumps(data))
        return SwaggerParser.parse(spec_file)

    return _parse
