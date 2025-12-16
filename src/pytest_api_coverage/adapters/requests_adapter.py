"""Requests library adapter using monkeypatch approach."""

import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
import requests.sessions

from pytest_api_coverage.collector import CoverageCollector
from pytest_api_coverage.models import HTTPInteraction, HTTPRequest, HTTPResponse


class RequestsAdapter:
    """Adapter for the requests library.

    Patches requests.sessions.Session.request to intercept all HTTP calls.
    Thread-safe with install/uninstall support.
    """

    _lock = threading.Lock()
    _installed: bool = False
    _original_request: Callable[..., Any] | None = None
    _collector: CoverageCollector | None = None

    @classmethod
    def install(cls, collector: CoverageCollector) -> None:
        """Install adapter to intercept requests library traffic.

        Args:
            collector: CoverageCollector instance to record interactions
        """
        with cls._lock:
            if cls._installed:
                return

            cls._collector = collector
            cls._original_request = requests.sessions.Session.request

            def patched_request(
                self: requests.Session,
                method: str,
                url: str,
                **kwargs: Any,
            ) -> requests.Response:
                start_time = time.perf_counter()
                timestamp = datetime.now(UTC)

                # Call original method
                response = cls._original_request(self, method, url, **kwargs)  # type: ignore[misc]

                duration_ms = (time.perf_counter() - start_time) * 1000

                # Record interaction (never break tests)
                try:
                    cls._record_interaction(
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

            requests.sessions.Session.request = patched_request  # type: ignore[method-assign]
            cls._installed = True

    @classmethod
    def uninstall(cls) -> None:
        """Uninstall adapter and restore original behavior."""
        with cls._lock:
            if not cls._installed:
                return

            if cls._original_request is not None:
                requests.sessions.Session.request = cls._original_request  # type: ignore[method-assign]
                cls._original_request = None

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
        kwargs: dict[str, Any],
        response: requests.Response,
        timestamp: datetime,
        duration_ms: float,
    ) -> None:
        """Record HTTP interaction to collector."""
        if cls._collector is None:
            return

        # Parse URL
        parsed = urlparse(url)

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
            url=str(response.url) if response.url else url,
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

        # Build response model
        http_response = HTTPResponse(
            status_code=response.status_code,
            headers=resp_headers,
            content_type=resp_content_type,
            body_size=len(response.content) if response.content else 0,
        )

        # Create and record interaction
        interaction = HTTPInteraction(
            request=http_request,
            response=http_response,
            timestamp=timestamp,
            duration_ms=duration_ms,
        )

        cls._collector.record(interaction)
