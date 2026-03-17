"""MultiSpecOrchestrator — routes HTTP interactions to per-spec reporters."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from pytest_api_coverage.config.settings import CoverageSettings, SpecConfig
from pytest_api_coverage.reporter import CoverageReporter
from pytest_api_coverage.schemas import SwaggerParser
from pytest_api_coverage.utils import normalize_origin
from pytest_api_coverage.writers import write_reports

logger = logging.getLogger("pytest_api_coverage")


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
                origins = {normalize_origin(u) for u in spec.api_urls}
                reporter = CoverageReporter(
                    swagger_spec,
                    include_base_urls=origins,
                )
                self._reporters[spec.name] = reporter
                self._specs.append(spec)
            except Exception as e:
                logger.warning("Failed to load spec '%s': %s", spec.name, e, exc_info=True)

    def _warn_overlapping_urls(self) -> None:
        """Check for URL overlap across specs and warn. Uses normalized origin for comparison."""
        seen: dict[str, str] = {}
        for spec in self._specs:
            for url in spec.api_urls:
                normalized = normalize_origin(url)
                if normalized in seen:
                    logger.warning(
                        "URL '%s' appears in both '%s' and '%s' specs. First-match-wins applies.",
                        normalized,
                        seen[normalized],
                        spec.name,
                    )
                else:
                    seen[normalized] = spec.name

    def _matches_spec(self, request_url: str, spec_url: str) -> bool:
        """Check if request_url matches spec_url (origin + path prefix).

        Trailing-slash safe: ``/auth`` matches ``/auth/users`` but NOT
        ``/authentic`` (the ``+ "/"`` guard prevents partial-segment matches).
        """
        parsed_req = urlparse(request_url)
        parsed_spec = urlparse(spec_url)

        req_origin = f"{parsed_req.scheme}://{parsed_req.netloc}"
        spec_origin = f"{parsed_spec.scheme}://{parsed_spec.netloc}"

        if req_origin != spec_origin:
            return False

        spec_path = parsed_spec.path or "/"
        req_path = parsed_req.path or "/"

        # Trailing-slash-safe prefix check: /auth must match /auth/users but NOT /authentic
        normalized_spec = spec_path.rstrip("/")
        return req_path == spec_path or req_path.startswith(normalized_spec + "/")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def specs(self) -> list[SpecConfig]:
        """Read-only view of loaded specs."""
        return self._specs

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
            for spec_url in spec.api_urls:
                if self._matches_spec(url, spec_url):
                    return spec.name
        return None

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

    def generate_all_reports(self) -> None:
        """Write prefixed report files for each loaded spec.

        A no-op when ``_specs`` is empty (e.g. all specs failed to load).
        """
        for spec in self._specs:
            reporter = self._reporters.get(spec.name)
            if reporter is None:
                continue
            report_data = reporter.generate_report()
            written = write_reports(
                report_data,
                self.settings.output_dir,
                self.settings.formats,
                prefix=spec.name,
            )
            if written:
                logger.info("Reports for '%s' written to: %s", spec.name, self.settings.output_dir)
