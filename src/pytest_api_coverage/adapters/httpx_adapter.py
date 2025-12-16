"""HTTPX library adapter using monkeypatch approach."""

import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from pytest_api_coverage.collector import CoverageCollector
from pytest_api_coverage.models import HTTPInteraction, HTTPRequest, HTTPResponse

if TYPE_CHECKING:
    import httpx


class HttpxAdapter:
    """Adapter for the httpx library.

    Patches httpx.Client.request and httpx.AsyncClient.request.
    Supports both sync and async clients.
    Thread-safe with install/uninstall support.
    """

    _lock = threading.Lock()
    _installed: bool = False
    _original_request: Callable[..., Any] | None = None
    _original_async_request: Callable[..., Any] | None = None
    _collector: CoverageCollector | None = None

    @classmethod
    def install(cls, collector: CoverageCollector) -> None:
        """Install adapter to intercept httpx library traffic.

        Args:
            collector: CoverageCollector instance to record interactions
        """
        if not HTTPX_AVAILABLE:
            return  # httpx not installed, skip silently

        with cls._lock:
            if cls._installed:
                return

            cls._collector = collector

            # Patch sync Client.request
            cls._original_request = httpx.Client.request

            def patched_request(
                self: "httpx.Client",
                method: str,
                url: "httpx.URL | str",
                **kwargs: Any,
            ) -> "httpx.Response":
                start_time = time.perf_counter()
                timestamp = datetime.now(UTC)

                response = cls._original_request(self, method, url, **kwargs)  # type: ignore[misc]

                duration_ms = (time.perf_counter() - start_time) * 1000

                try:
                    cls._record_interaction(
                        method=method,
                        url=str(url),
                        response=response,
                        timestamp=timestamp,
                        duration_ms=duration_ms,
                    )
                except Exception:
                    pass  # Never let coverage tracking break tests

                return response

            httpx.Client.request = patched_request  # type: ignore[method-assign]

            # Patch async AsyncClient.request
            cls._original_async_request = httpx.AsyncClient.request

            async def patched_async_request(
                self: "httpx.AsyncClient",
                method: str,
                url: "httpx.URL | str",
                **kwargs: Any,
            ) -> "httpx.Response":
                start_time = time.perf_counter()
                timestamp = datetime.now(UTC)

                response = await cls._original_async_request(self, method, url, **kwargs)  # type: ignore[misc]

                duration_ms = (time.perf_counter() - start_time) * 1000

                try:
                    cls._record_interaction(
                        method=method,
                        url=str(url),
                        response=response,
                        timestamp=timestamp,
                        duration_ms=duration_ms,
                    )
                except Exception:
                    pass  # Never let coverage tracking break tests

                return response

            httpx.AsyncClient.request = patched_async_request  # type: ignore[method-assign]

            cls._installed = True

    @classmethod
    def uninstall(cls) -> None:
        """Uninstall adapter and restore original behavior."""
        if not HTTPX_AVAILABLE:
            return

        with cls._lock:
            if not cls._installed:
                return

            if cls._original_request is not None:
                httpx.Client.request = cls._original_request  # type: ignore[method-assign]
                cls._original_request = None

            if cls._original_async_request is not None:
                httpx.AsyncClient.request = cls._original_async_request  # type: ignore[method-assign]
                cls._original_async_request = None

            cls._collector = None
            cls._installed = False

    @classmethod
    def is_installed(cls) -> bool:
        """Check if adapter is currently installed."""
        return cls._installed

    @classmethod
    def _record_interaction(
        cls,
        method: str,
        url: str,
        response: "httpx.Response",
        timestamp: datetime,
        duration_ms: float,
    ) -> None:
        """Record HTTP interaction to collector."""
        if cls._collector is None:
            return

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
        http_request = HTTPRequest(
            method=method.upper(),
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

        # Calculate body size
        body_size = 0
        try:
            body_size = len(response.content)
        except Exception:
            pass

        # Build response model
        http_response = HTTPResponse(
            status_code=response.status_code,
            headers=resp_headers,
            content_type=resp_content_type,
            body_size=body_size,
        )

        # Create and record interaction
        interaction = HTTPInteraction(
            request=http_request,
            response=http_response,
            timestamp=timestamp,
            duration_ms=duration_ms,
        )

        cls._collector.record(interaction)
