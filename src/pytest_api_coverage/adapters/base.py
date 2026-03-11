"""Protocol definition for HTTP library adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pytest_api_coverage.collector import CoverageCollector


class HttpAdapterProtocol(Protocol):
    """Protocol for HTTP library adapters (instance-based)."""

    def __init__(self, collector: CoverageCollector) -> None: ...

    def install(self) -> None: ...

    def uninstall(self) -> None: ...

    def is_installed(self) -> bool: ...
