"""Thread-safe collector for HTTP interactions."""

import decimal
import logging
import threading
from enum import Enum
from queue import Empty, Queue
from typing import Any, Protocol, runtime_checkable

from pytest_api_coverage.models import HTTPInteraction

logger = logging.getLogger("pytest_api_coverage")


@runtime_checkable
class HTTPInterceptor(Protocol):
    """Protocol for objects that can receive HTTP interactions."""

    def record(self, interaction: HTTPInteraction) -> None:
        """Record an HTTP interaction."""
        ...


class CoverageCollector:
    """Thread-safe collector for HTTP coverage data.

    Uses Queue for thread-safe recording and Lock for data access.
    Works correctly in:
    - Single-threaded pytest
    - Multi-threaded test execution
    - pytest-xdist workers
    """

    def __init__(self) -> None:
        self._queue: Queue[HTTPInteraction] = Queue()
        self._data: list[HTTPInteraction] = []
        self._lock = threading.Lock()
        self._current_test: str | None = None

    def set_current_test(self, test_name: str | None) -> None:
        """Set the current test name for attribution."""
        with self._lock:
            self._current_test = test_name

    def record(self, interaction: HTTPInteraction) -> None:
        """Thread-safe recording of HTTP interaction.

        If test_name is not set on interaction, uses current test context.
        """
        if interaction.test_name is None:
            with self._lock:
                current = self._current_test
            if current:
                interaction = HTTPInteraction(
                    request=interaction.request,
                    response=interaction.response,
                    timestamp=interaction.timestamp,
                    duration_ms=interaction.duration_ms,
                    test_name=current,
                )
        self._queue.put(interaction)

    def has_data(self) -> bool:
        """Check if any data has been collected."""
        self._drain_queue()
        with self._lock:
            return len(self._data) > 0

    def get_data(self) -> list[dict[str, Any]]:
        """Return all collected data as serializable dicts."""
        self._drain_queue()
        with self._lock:
            data = [self._interaction_to_dict(i) for i in self._data]
        logger.debug("Collected %d interactions", len(data))
        return data

    def clear(self) -> None:
        """Clear all collected data."""
        self._drain_queue()
        with self._lock:
            self._data.clear()

    def _drain_queue(self) -> None:
        """Move all queued items to the data list."""
        with self._lock:
            while True:
                try:
                    item = self._queue.get_nowait()
                    self._data.append(item)
                except Empty:
                    break

    @staticmethod
    def _make_serializable(value: Any) -> Any:
        """Recursively convert value to execnet-serializable basic Python types."""
        if isinstance(value, dict):
            return {k: CoverageCollector._make_serializable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [CoverageCollector._make_serializable(item) for item in value]
        if isinstance(value, (str, int, float, bool, bytes, type(None))):
            return value
        # Decimal → float, enums → their value, anything else → str
        if isinstance(value, decimal.Decimal):
            return float(value)
        if isinstance(value, Enum):
            return CoverageCollector._make_serializable(value.value)
        return str(value)

    def _interaction_to_dict(self, interaction: HTTPInteraction) -> dict[str, Any]:
        """Convert interaction to serializable dict."""
        return {
            "request": {
                "method": interaction.request.method,
                "url": interaction.request.url,
                "path": interaction.request.path,
                "host": interaction.request.host,
                "headers": dict(interaction.request.headers),
                "query_params": self._make_serializable(dict(interaction.request.query_params)),
                "body": self._make_serializable(interaction.request.body),
                "content_type": interaction.request.content_type,
            },
            "response": {
                "status_code": interaction.response.status_code,
                "headers": dict(interaction.response.headers),
                "content_type": interaction.response.content_type,
                "body_size": interaction.response.body_size,
            },
            "timestamp": interaction.timestamp.isoformat(),
            "duration_ms": interaction.duration_ms,
            "test_name": interaction.test_name,
        }
