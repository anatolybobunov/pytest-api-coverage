"""HTTPX library adapter using monkeypatch approach."""

import logging
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger("pytest_api_coverage")

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from pytest_api_coverage.collector import CoverageCollector
from pytest_api_coverage.models import HTTPInteraction, HTTPRequest, HTTPResponse

_PATCH_SENTINEL = "_pytest_api_coverage_patched"

if TYPE_CHECKING:
    import httpx


class HttpxAdapter:
    """Adapter for the httpx library.

    Patches httpx.Client.request and httpx.AsyncClient.request.
    Supports both sync and async clients.
    Thread-safe with install/uninstall support.
    """

    def __init__(self, collector: CoverageCollector) -> None:
        self._collector = collector
        self._lock = threading.Lock()
        self._installed: bool = False
        self._original_request: Callable[..., Any] | None = None
        self._original_async_request: Callable[..., Any] | None = None
        self._patched_request: Callable[..., Any] | None = None
        self._patched_async_request: Callable[..., Any] | None = None

    def install(self) -> None:
        """Install adapter to intercept httpx library traffic."""
        if not HTTPX_AVAILABLE:
            return  # httpx not installed, skip silently

        with self._lock:
            if self._installed:
                return

            collector = self._collector

            # Patch sync Client.request — if already patched by another instance, skip entirely.
            # This instance owns nothing, so _installed stays False.
            original = httpx.Client.request
            if getattr(original, _PATCH_SENTINEL, False):
                return  # Another instance already patched — do not claim ownership

            self._original_request = original

            def patched_request(
                self: "httpx.Client",
                method: str,
                url: "httpx.URL | str",
                **kwargs: Any,
            ) -> "httpx.Response":
                start_time = time.perf_counter()
                timestamp = datetime.now(UTC)

                response = original(self, method, url, **kwargs)

                duration_ms = (time.perf_counter() - start_time) * 1000

                try:
                    _record_httpx_interaction(
                        collector=collector,
                        method=method,
                        url=str(url),
                        response=response,
                        timestamp=timestamp,
                        duration_ms=duration_ms,
                    )
                except Exception:
                    logger.warning("httpx sync: Failed to record %s %s", method, url, exc_info=True)
                    collector.record_error()

                return response

            setattr(patched_request, _PATCH_SENTINEL, True)
            httpx.Client.request = patched_request  # type: ignore[method-assign]
            self._patched_request = patched_request

            # Patch async AsyncClient.request independently — a prior adapter may have patched
            # only the async client, but since the sync guard above passed, this instance owns
            # at least the sync patch.  Async is best-effort.
            original_async = httpx.AsyncClient.request
            if not getattr(original_async, _PATCH_SENTINEL, False):
                self._original_async_request = original_async

                async def patched_async_request(
                    self: "httpx.AsyncClient",
                    method: str,
                    url: "httpx.URL | str",
                    **kwargs: Any,
                ) -> "httpx.Response":
                    start_time = time.perf_counter()
                    timestamp = datetime.now(UTC)

                    response = await original_async(self, method, url, **kwargs)

                    duration_ms = (time.perf_counter() - start_time) * 1000

                    try:
                        _record_httpx_interaction(
                            collector=collector,
                            method=method,
                            url=str(url),
                            response=response,
                            timestamp=timestamp,
                            duration_ms=duration_ms,
                        )
                    except Exception:
                        logger.warning("httpx async: Failed to record %s %s", method, url, exc_info=True)
                        collector.record_error()

                    return response

                setattr(patched_async_request, _PATCH_SENTINEL, True)
                httpx.AsyncClient.request = patched_async_request  # type: ignore[method-assign]
                self._patched_async_request = patched_async_request

            self._installed = True  # Only reached when sync patch was applied by this instance
            logger.debug("Patched httpx.Client.request and httpx.AsyncClient.request for HTTP interception")

    def uninstall(self) -> None:
        """Uninstall adapter and restore original behavior."""
        if not HTTPX_AVAILABLE:
            return

        with self._lock:
            if not self._installed:
                return

            current_sync = getattr(httpx.Client, 'request', None)
            if current_sync is self._patched_request and self._original_request is not None:
                httpx.Client.request = self._original_request  # type: ignore[method-assign]
            self._original_request = None
            self._patched_request = None

            current_async = getattr(httpx.AsyncClient, 'request', None)
            if current_async is self._patched_async_request and self._original_async_request is not None:
                httpx.AsyncClient.request = self._original_async_request  # type: ignore[method-assign]
            self._original_async_request = None
            self._patched_async_request = None

            self._installed = False

    def is_installed(self) -> bool:
        """Check if adapter is currently installed."""
        return self._installed


def _record_httpx_interaction(
    collector: CoverageCollector,
    method: str,
    url: str,
    response: "httpx.Response",
    timestamp: datetime,
    duration_ms: float,
) -> None:
    """Record HTTP interaction to collector."""
    # Parse URL from response (contains resolved URL with base_url)
    actual_url = str(response.url)
    parsed = urlparse(actual_url)

    # Extract headers from response.request
    req_headers = {k: v for k, v in response.request.headers.items()}

    # Determine content type
    content_type = None
    for key, value in req_headers.items():
        if key.lower() == "content-type":
            content_type = value
            break

    # Extract query params from URL
    query_params: dict[str, Any] = {}
    if parsed.query:
        query_params = parse_qs(parsed.query)

    # Extract body from request
    body: Any = None
    if response.request.content:
        try:
            body = response.request.content.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            body = f"<binary: {len(response.request.content)} bytes>"

    # Build request model
    # Use response.request.method to capture the final method after any redirects
    http_request = HTTPRequest(
        method=str(response.request.method).upper(),
        url=actual_url,
        path=parsed.path or "/",
        host=parsed.netloc,
        headers=req_headers,
        query_params=query_params,
        body=body,
        content_type=content_type,
    )

    # Extract response headers
    resp_headers = {k: v for k, v in response.headers.items()}
    resp_content_type = response.headers.get("content-type")

    # Calculate body size — avoid reading an unconsumed stream.
    body_size = 0
    try:
        if hasattr(response, 'is_stream_consumed'):
            if response.is_stream_consumed:
                body_size = len(response.content)
            else:
                body_size = response.num_bytes_downloaded
        else:
            body_size = len(response.content)
    except Exception:
        logger.debug("httpx: Failed to get response body size", exc_info=True)

    # Build response model
    http_response = HTTPResponse(
        status_code=response.status_code,
        headers=resp_headers,
        content_type=resp_content_type,
        body_size=body_size,
    )

    interaction = HTTPInteraction(
        request=http_request,
        response=http_response,
        timestamp=timestamp,
        duration_ms=duration_ms,
    )

    collector.record(interaction)
