"""Data models for HTTP interaction tracking and API coverage."""

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


@dataclass
class EndpointCoverage:
    """Coverage data for a single API endpoint."""

    method: str
    path: str
    hit_count: int = 0
    response_codes: dict[int, int] = field(default_factory=dict)  # status_code -> count
    test_names: set[str] = field(default_factory=set)

    @property
    def is_covered(self) -> bool:
        """Check if endpoint has been hit at least once."""
        return self.hit_count > 0

    def record_hit(self, status_code: int, test_name: str | None = None) -> None:
        """Record a hit on this endpoint."""
        self.hit_count += 1
        self.response_codes[status_code] = self.response_codes.get(status_code, 0) + 1
        if test_name:
            self.test_names.add(test_name)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for report output."""
        return {
            "method": self.method,
            "path": self.path,
            "hit_count": self.hit_count,
            "is_covered": self.is_covered,
            "response_codes": self.response_codes,
            "test_names": sorted(self.test_names),
        }


@dataclass
class MethodCoverage:
    """Coverage data for a single method on an endpoint path."""

    method: str
    hit_count: int = 0
    response_codes: dict[int, int] = field(default_factory=dict)
    test_names: set[str] = field(default_factory=set)

    @property
    def is_covered(self) -> bool:
        """Check if method has been hit at least once."""
        return self.hit_count > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for report output."""
        return {
            "method": self.method,
            "hit_count": self.hit_count,
            "is_covered": self.is_covered,
            "response_codes": self.response_codes,
            "test_names": sorted(self.test_names),
        }


@dataclass
class PathCoverage:
    """Coverage data for an API path (grouped by methods)."""

    path: str
    methods: list[MethodCoverage] = field(default_factory=list)

    @property
    def total_hit_count(self) -> int:
        """Total hits across all methods."""
        return sum(m.hit_count for m in self.methods)

    @property
    def is_covered(self) -> bool:
        """Check if any method has been hit."""
        return any(m.is_covered for m in self.methods)

    @property
    def all_methods_covered(self) -> bool:
        """Check if all methods have been hit."""
        return all(m.is_covered for m in self.methods)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for report output."""
        return {
            "path": self.path,
            "hit_count": self.total_hit_count,
            "is_covered": self.is_covered,
            "all_methods_covered": self.all_methods_covered,
            "methods": [m.to_dict() for m in self.methods],
        }
