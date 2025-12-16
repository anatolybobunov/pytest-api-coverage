"""Data models for HTTP interaction tracking."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from typing import Any


@dataclass(frozen=True)
class HTTPRequest:
    """Immutable representation of an HTTP request."""

    method: str
    url: str
    path: str
    host: str
    headers: dict[str, str] = field(default_factory=dict)
    query_params: dict[str, Any] = field(default_factory=dict)
    body: Any | None = None
    content_type: str | None = None


@dataclass(frozen=True)
class HTTPResponse:
    """Immutable representation of an HTTP response."""

    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    content_type: str | None = None
    body_size: int = 0


@dataclass
class HTTPInteraction:
    """Complete HTTP request-response interaction.

    Note: Not frozen because test_name may be assigned after creation
    when the collector knows the current test context.
    """

    request: HTTPRequest
    response: HTTPResponse
    timestamp: datetime = field(default_factory=partial(datetime.now, UTC))
    duration_ms: float = 0.0
    test_name: str | None = None
