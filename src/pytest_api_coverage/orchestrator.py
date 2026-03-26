"""MultiSpecOrchestrator — routes HTTP interactions to per-spec reporters."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from pytest_api_coverage.config.settings import CoverageSettings, SpecConfig
from pytest_api_coverage.reporter import CoverageReporter
from pytest_api_coverage.schemas import SwaggerParser, format_spec_load_error
from pytest_api_coverage.utils import matches_filter_value
from pytest_api_coverage.writers import write_reports

logger = logging.getLogger("pytest_api_coverage")


def _auto_strip_prefixes(api_filters: list[str]) -> list[str]:
    """Extract path portions from api_filters URLs to use as strip prefixes.

    Example: 'http://host/symboldb' → ['/symboldb']
    Bare hostnames or filters with no meaningful path return nothing.
    """
    prefixes = []
    for f in api_filters:
        parsed = urlparse(f if f.startswith(("http://", "https://")) else f"http://{f}")
        path = parsed.path.rstrip("/")
        if path and path != "/":
            prefixes.append(path)
    return prefixes


class MultiSpecOrchestrator:
    """Central coordination layer for multi-spec API coverage.

    Creates one CoverageReporter per SpecConfig at initialisation, routes
    HTTP interactions to the correct reporter using origin + path-prefix
    matching (first-match-wins), and exposes ``generate_all_reports()`` for
    the plugin to call at session end.
    """

    def __init__(self, settings: CoverageSettings) -> None:
        self.settings = settings
        self.unmatched_count: int = 0
        self._reporters: dict[str, CoverageReporter] = {}
        self._specs: list[SpecConfig] = []
        self._failed_specs: list[tuple[str, str]] = []
        self._load_all_specs()
        self._warn_overlapping_urls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_all_specs(self) -> None:
        """Load SwaggerSpec for each SpecConfig. Warn + skip on failure. Never raise."""
        for spec in self.settings.specs:
            try:
                source = spec.swagger_url if spec.swagger_url else spec.swagger_path
                if source is None:
                    raise ValueError(f"Spec '{spec.name}' has no swagger_url or swagger_path configured")
                swagger_spec = SwaggerParser.parse(source)
                # Combine auto-derived prefixes (from api_filters paths) with explicit ones
                auto = _auto_strip_prefixes(spec.api_filters)
                seen: set[str] = set()
                combined: list[str] = []
                for p in auto + spec.strip_prefixes:
                    if p not in seen:
                        seen.add(p)
                        combined.append(p)
                reporter = CoverageReporter(
                    swagger_spec,
                    include_base_urls=set(spec.api_filters),
                    strip_prefixes=combined or None,
                )
                self._reporters[spec.name] = reporter
                self._specs.append(spec)
            except Exception as e:
                msg = format_spec_load_error(e)
                logger.warning("Failed to load spec '%s': %s", spec.name, msg)
                logger.debug("Traceback for failed spec '%s':", spec.name, exc_info=True)
                self._failed_specs.append((spec.name, msg))

    def _warn_overlapping_urls(self) -> None:
        """Check for URL overlap across specs and warn."""
        seen: dict[str, str] = {}
        for spec in self._specs:
            for filter_value in spec.api_filters:
                if filter_value in seen:
                    logger.warning(
                        "URL '%s' appears in both '%s' and '%s' specs. First-match-wins applies.",
                        filter_value,
                        seen[filter_value],
                        spec.name,
                    )
                else:
                    seen[filter_value] = spec.name

    def _matches_spec(self, request_url: str, filter_value: str) -> bool:
        """Check if request_url matches filter_value (origin + path prefix).

        Delegates to :func:`pytest_api_coverage.utils.matches_filter_value`.
        """
        return matches_filter_value(request_url, filter_value)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def specs(self) -> list[SpecConfig]:
        """Read-only view of loaded specs."""
        return self._specs

    @property
    def failed_specs(self) -> list[tuple[str, str]]:
        """Read-only view of specs that failed to load, as (name, error) pairs."""
        return self._failed_specs

    @property
    def reporters(self) -> dict[str, CoverageReporter]:
        """Read-only view of spec reporters."""
        return self._reporters

    def route_interaction(self, interaction: dict[str, Any]) -> str | None:
        """Return the spec name that owns this interaction, or None.

        Uses first-match-wins across self._specs in insertion order.
        Never raises for unmatched requests.
        """
        url = interaction.get("request", {}).get("url", "")
        for spec in self._specs:
            for filter_value in spec.api_filters:
                if self._matches_spec(url, filter_value):
                    return spec.name
        return None

    def record_interaction(
        self, method: str, url: str, status_code: int, test_name: str
    ) -> None:
        """Convenience wrapper: build an interaction dict and route it.

        Equivalent to calling ``process_interactions`` with a single interaction
        constructed from the given parameters.
        """
        from urllib.parse import urlparse as _urlparse

        parsed = _urlparse(url)
        path = parsed.path or "/"
        interaction: dict[str, Any] = {
            "request": {"url": url, "method": method, "path": path},
            "response": {"status_code": status_code},
            "test_name": test_name,
        }
        self.process_interactions([interaction])

    def process_interactions(self, interactions: list[dict[str, Any]]) -> None:
        """Route each interaction to its reporter.

        Interactions that match no spec URL increment ``unmatched_count``.
        """
        for interaction in interactions:
            spec_name = self.route_interaction(interaction)
            if spec_name and spec_name in self._reporters:
                self._reporters[spec_name].process_interactions([interaction])
            else:
                self.unmatched_count += 1

    def generate_all_reports(self) -> dict[str, Any]:
        """Write prefixed report files for each loaded spec and return the generated data.

        A no-op when ``_specs`` is empty (e.g. all specs failed to load).

        Returns:
            Mapping of spec name to its generated report dict.
        """
        all_reports: dict[str, Any] = {}
        for spec in self._specs:
            reporter = self._reporters.get(spec.name)
            if reporter is None:
                continue
            report_data = reporter.generate_report()
            all_reports[spec.name] = report_data
            written = write_reports(
                report_data,
                self.settings.output_dir,
                self.settings.formats,
                prefix=spec.name,
            )
            if written:
                logger.info("Reports for '%s' written to: %s", spec.name, self.settings.output_dir)
        return all_reports
