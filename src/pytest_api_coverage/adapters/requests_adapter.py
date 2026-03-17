"""Requests library adapter using monkeypatch approach."""

import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    import requests
    import requests.sessions

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from pytest_api_coverage.collector import CoverageCollector
from pytest_api_coverage.models import HTTPInteraction, HTTPRequest, HTTPResponse

_PATCH_SENTINEL = "_pytest_api_coverage_patched"


class RequestsAdapter:
    """Adapter for the requests library.

    Patches requests.sessions.Session.request to intercept all HTTP calls.
    Thread-safe with install/uninstall support.
    """

    def __init__(self, collector: CoverageCollector) -> None:
        self._collector = collector
        self._lock = threading.Lock()
        self._installed: bool = False
        self._original_request: Callable[..., Any] | None = None

    def install(self) -> None:
        """Install adapter to intercept requests library traffic."""
        if not REQUESTS_AVAILABLE:
            return  # requests not installed, skip silently
        with self._lock:
            if self._installed:
                return

            collector = self._collector
            original = requests.sessions.Session.request
            if getattr(original, _PATCH_SENTINEL, False):
                # Another adapter instance already patched this method — skip to avoid stacking
                return

            self._original_request = original

            def patched_request(
                self: requests.Session,
                method: str,
                url: str,
                **kwargs: Any,
            ) -> requests.Response:
                start_time = time.perf_counter()
                timestamp = datetime.now(UTC)

                response = original(self, method, url, **kwargs)

                duration_ms = (time.perf_counter() - start_time) * 1000

                try:
                    _record_requests_interaction(
                        collector=collector,
                        method=method,
                        url=url,
                        kwargs=kwargs,
                        response=response,
                        timestamp=timestamp,
                        duration_ms=duration_ms,
                    )
                except Exception:
                    pass  # Never let coverage tracking break tests

                return response

            setattr(patched_request, _PATCH_SENTINEL, True)
            requests.sessions.Session.request = patched_request  # type: ignore[assignment,method-assign]
            self._installed = True

    def uninstall(self) -> None:
        """Uninstall adapter and restore original behavior."""
        if not REQUESTS_AVAILABLE:
            return
        with self._lock:
            if not self._installed:
                return

            if self._original_request is not None:
                requests.sessions.Session.request = self._original_request  # type: ignore[method-assign]
                self._original_request = None

            self._installed = False

    def is_installed(self) -> bool:
        """Check if adapter is currently installed."""
        return self._installed


def _record_requests_interaction(
    collector: CoverageCollector,
    method: str,
    url: str,
    kwargs: dict[str, Any],
    response: requests.Response,
    timestamp: datetime,
    duration_ms: float,
) -> None:
    """Record HTTP interaction to collector."""
    # Parse URL
    parsed = urlparse(url)
    final_url = str(response.url) if response.url else url
    final_parsed = urlparse(final_url)

    # Extract headers from response.request (contains actual sent headers)
    req_headers: dict[str, str] = {}
    if response.request is not None:
        req_headers = {k: v for k, v in response.request.headers.items()}

    # Determine content type
    content_type = None
    for key, value in req_headers.items():
        if key.lower() == "content-type":
            content_type = value
            break

    # Extract query params
    query_params: dict[str, Any] = {}
    if parsed.query:
        query_params = parse_qs(parsed.query)
    if kwargs.get("params"):
        params = kwargs["params"]
        if isinstance(params, dict):
            query_params.update(params)

    # Extract body
    body = kwargs.get("json") or kwargs.get("data")

    # Build request model
    http_request = HTTPRequest(
        method=method.upper(),
        url=final_url,
        path=final_parsed.path or "/",
        host=final_parsed.netloc,
        headers=req_headers,
        query_params=query_params,
        body=body,
        content_type=content_type,
    )

    # Extract response headers
    resp_headers = {k: v for k, v in response.headers.items()}
    resp_content_type = response.headers.get("content-type")

    # Build response model
    http_response = HTTPResponse(
        status_code=response.status_code,
        headers=resp_headers,
        content_type=resp_content_type,
        body_size=len(response.content) if response.content else 0,
    )

    interaction = HTTPInteraction(
        request=http_request,
        response=http_response,
        timestamp=timestamp,
        duration_ms=duration_ms,
    )

    collector.record(interaction)
