"""HTTP library adapters for request/response interception."""

from pytest_api_coverage.adapters.httpx_adapter import HttpxAdapter
from pytest_api_coverage.adapters.requests_adapter import RequestsAdapter

ADAPTER_REGISTRY: list[type] = [RequestsAdapter, HttpxAdapter]

__all__ = ["RequestsAdapter", "HttpxAdapter", "ADAPTER_REGISTRY"]
