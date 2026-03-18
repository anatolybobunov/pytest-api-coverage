"""pytest-api-coverage - API test coverage analysis plugin."""

from importlib.metadata import version

from pytest_api_coverage.collector import CoverageCollector, HTTPInterceptor
from pytest_api_coverage.models import (
    EndpointCoverage,
    HTTPInteraction,
    HTTPRequest,
    HTTPResponse,
    MethodCoverage,
    PathCoverage,
)

__version__ = version("pytest-api-coverage")
__all__ = [
    "CoverageCollector",
    "HTTPInterceptor",
    "HTTPInteraction",
    "HTTPRequest",
    "HTTPResponse",
    "EndpointCoverage",
    "MethodCoverage",
    "PathCoverage",
]
