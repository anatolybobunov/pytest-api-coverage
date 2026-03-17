"""Pytest plugin entry point with HTTP monkeypatching."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from pytest_api_coverage.adapters import ADAPTER_REGISTRY
from pytest_api_coverage.collector import CoverageCollector
from pytest_api_coverage.config.settings import CoverageSettings
from pytest_api_coverage.orchestrator import MultiSpecOrchestrator
from pytest_api_coverage.reporter import CoverageReporter
from pytest_api_coverage.schemas import SwaggerParser, SwaggerSpec
from pytest_api_coverage.terminal import print_multi_spec_summary, print_terminal_summary
from pytest_api_coverage.writers import write_reports

if TYPE_CHECKING:
    from pytest import Config, Item, Parser, Session, TerminalReporter

logger = logging.getLogger("pytest_api_coverage")


def pytest_addoption(parser: Parser) -> None:
    """Add CLI options for API coverage."""
    group = parser.getgroup("api-coverage")
    group.addoption(
        "--coverage-spec",
        dest="coverage_spec",
        type=str,
        default=None,
        help="Path or URL to OpenAPI spec (swagger.json/yaml or remote URL)",
    )
    group.addoption(
        "--coverage-output",
        dest="coverage_output",
        type=str,
        default="coverage-output",
        help="Output directory for coverage reports",
    )
    group.addoption(
        "--coverage-format",
        dest="coverage_format",
        type=str,
        default="json,csv,html",
        help="Report formats (comma-separated): json,csv,html",
    )
    group.addoption(
        "--coverage-strip-prefix",
        dest="coverage_strip_prefix",
        type=str,
        default=None,
        help="Additional path prefixes to strip (comma-separated). Example: /v1,/api/v2",
    )
    group.addoption(
        "--coverage-split-by-origin",
        dest="coverage_split_by_origin",
        action="store_true",
        default=False,
        help="Generate separate coverage buckets per origin in reports",
    )
    group.addoption(
        "--coverage-config",
        dest="coverage_config",
        type=str,
        default=None,
        help="Path to api-coverage config file (YAML/JSON) for multi-spec configuration",
    )
    group.addoption(
        "--coverage-spec-name",
        dest="coverage_spec_name",
        type=str,
        default=None,
        help="Name for the spec (used with --coverage-spec and --coverage-spec-api-url)",
    )
    group.addoption(
        "--coverage-spec-api-url",
        dest="coverage_spec_api_url",
        action="append",
        default=None,
        help="API base URL(s) for the spec (repeatable). Example: --coverage-spec-api-url https://api.example.com",
    )


def pytest_configure(config: Config) -> None:
    """Register the appropriate plugin based on execution mode."""
    if not CoverageSettings.from_pytest_config(config).is_enabled():
        return  # Coverage not enabled

    # Determine execution mode
    if hasattr(config, "workerinput"):
        # Worker node in xdist
        plugin = CoverageWorkerPlugin(config)
    elif _is_xdist_master(config):
        # Master node with active xdist workers
        plugin = CoverageMasterPlugin(config)
    else:
        # Single process mode
        plugin = CoverageSinglePlugin(config)

    config._api_coverage_plugin = plugin  # type: ignore[attr-defined]
    config.pluginmanager.register(plugin, "api_coverage_plugin")


def _build_activity_line(settings: CoverageSettings) -> str | None:
    """Build the startup activity indicator line for the terminal.

    Returns a formatted string describing the active plugin mode, or None
    if neither swagger nor specs are configured (should not happen after
    is_enabled() check, but guard anyway).
    """
    if settings.specs:
        spec_names = ", ".join(s.name for s in settings.specs)
        return f"[api-coverage] Active | mode: multi-spec | specs: {spec_names} | output: {settings.output_dir}/"
    if settings.spec:
        stem = Path(str(settings.spec)).stem
        return f"[api-coverage] Active | mode: single-spec | spec: {stem} | output: {settings.output_dir}/"
    return None


def _is_xdist_master(config: Config) -> bool:
    """Check if we're running as xdist master with active workers.

    Returns True only if:
    - xdist plugin is available
    - -n option was specified with value > 0
    """
    if not config.pluginmanager.hasplugin("xdist"):
        return False
    numprocesses = getattr(config.option, "numprocesses", None)
    return numprocesses is not None and numprocesses > 0


class _InterceptionMixin:
    """Shared HTTP interception logic for single-process and worker plugins.

    Requires subclass to set:
        self.collector: CoverageCollector
        self._adapters: list[HttpAdapter]
    """

    collector: CoverageCollector
    _adapters: list[Any]

    @pytest.hookimpl
    def pytest_runtest_setup(self, item: Item) -> None:
        """Set current test name before test runs."""
        self.collector.set_current_test(item.nodeid)

    @pytest.hookimpl
    def pytest_runtest_teardown(self, item: Item) -> None:
        """Clear current test name after test completes."""
        self.collector.set_current_test(None)

    def _setup_http_interception(self) -> None:
        """Install HTTP adapters for requests and httpx."""
        for adapter in self._adapters:
            adapter.install()

    def _teardown_http_interception(self) -> None:
        """Uninstall HTTP adapters to prevent memory leaks."""
        for adapter in self._adapters:
            adapter.uninstall()


class _SwaggerLoadMixin:
    """Shared swagger loading logic for single-process and master plugins.

    Requires subclass to set:
        self.settings: CoverageSettings
    Sets:
        self.swagger_spec: SwaggerSpec | None
        self._swagger_load_error: str | None
    """

    settings: CoverageSettings
    swagger_spec: SwaggerSpec | None
    _swagger_load_error: str | None

    def _load_swagger(self) -> None:
        """Load and parse swagger specification."""
        if not self.settings.spec:
            return
        try:
            self.swagger_spec = SwaggerParser.parse(self.settings.spec)
        except Exception as e:
            self._swagger_load_error = str(e)
            logger.warning("Failed to load swagger: %s", e, exc_info=True)


class CoverageSinglePlugin(_InterceptionMixin, _SwaggerLoadMixin):
    """Coverage plugin for single-process test execution."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.settings = CoverageSettings.from_pytest_config(config)
        self.collector = CoverageCollector()
        self._adapters = [cls(self.collector) for cls in ADAPTER_REGISTRY]
        self.swagger_spec: SwaggerSpec | None = None
        self._swagger_load_error: str | None = None
        self._no_requests_captured: bool = False
        self.report_data: dict[str, Any] | None = None
        self.orchestrator: MultiSpecOrchestrator | None = None

    @pytest.hookimpl
    def pytest_sessionstart(self, session: Session) -> None:
        """Setup HTTP interception at session start."""
        self.settings.raise_if_error()  # raise deferred config errors here
        # Load all specs BEFORE installing HTTP adapters so that any remote spec
        # fetches (httpx.Client) are not intercepted and recorded as coverage data.
        self._load_swagger()
        if self.settings.specs:
            self.orchestrator = MultiSpecOrchestrator(self.settings)
        self._setup_http_interception()
        tr: TerminalReporter | None = session.config.pluginmanager.get_plugin("terminalreporter")
        if tr is not None:
            line = _build_activity_line(self.settings)
            if line is not None:
                tr.write_line(line)

    @pytest.hookimpl
    def pytest_sessionfinish(self, session: Session, exitstatus: int) -> None:
        """Generate coverage reports at session end."""
        if self.settings.specs and self.orchestrator:
            self.orchestrator.process_interactions(self.collector.get_data())
            self.orchestrator.generate_all_reports()
        elif self.swagger_spec:
            if self.collector.has_data():
                self._generate_report()
            else:
                self._no_requests_captured = True

    @pytest.hookimpl
    def pytest_terminal_summary(self, terminalreporter: TerminalReporter) -> None:
        """Print coverage summary to terminal."""
        if self.orchestrator:
            print_multi_spec_summary(terminalreporter, self.orchestrator)
        elif self.report_data:
            print_terminal_summary(terminalreporter, self.report_data, self.settings)
        elif self._swagger_load_error:
            terminalreporter.write_sep("=", "API Coverage Summary")
            terminalreporter.write_line(
                f"[api-coverage] No report generated — spec failed to load: {self._swagger_load_error}"
            )
        elif self._no_requests_captured:
            terminalreporter.write_sep("=", "API Coverage Summary")
            terminalreporter.write_line(
                "[api-coverage] 0 HTTP requests captured. "
                "Check that tests use 'requests' or 'httpx' directly and that "
                "mocking libraries are not intercepting at the socket level."
            )

    @pytest.hookimpl
    def pytest_unconfigure(self, config: Config) -> None:
        """Clean up adapters when pytest finishes."""
        self._teardown_http_interception()

    def _generate_report(self) -> None:
        """Generate coverage report using reporter."""
        if not self.swagger_spec:
            return

        reporter = CoverageReporter(
            self.swagger_spec,
            strip_prefixes=self.settings.strip_prefixes or None,
            split_by_origin=self.settings.split_by_origin,
        )
        reporter.process_interactions(self.collector.get_data())
        self.report_data = reporter.generate_report()

        # Write reports to files
        written = write_reports(self.report_data, self.settings.output_dir, self.settings.formats)
        if written:
            logger.info("Reports written to: %s", self.settings.output_dir)


class CoverageMasterPlugin(_SwaggerLoadMixin):
    """Coverage plugin for xdist master node."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.settings = CoverageSettings.from_pytest_config(config)
        self.worker_data: dict[str, Any] = {}
        self.swagger_spec: SwaggerSpec | None = None
        self._swagger_load_error: str | None = None
        self.report_data: dict[str, Any] | None = None
        self.orchestrator: MultiSpecOrchestrator | None = None

    @pytest.hookimpl
    def pytest_sessionstart(self, session: Session) -> None:
        """Load swagger and log plugin activity at session start."""
        self.settings.raise_if_error()  # raise deferred config errors here
        # Initialize orchestrator here (not in __init__) to ensure spec fetches
        # happen before HTTP adapters are installed.
        self._load_swagger()
        if self.settings.specs:
            self.orchestrator = MultiSpecOrchestrator(self.settings)
        tr: TerminalReporter | None = session.config.pluginmanager.get_plugin("terminalreporter")
        if tr is None:
            return
        line = _build_activity_line(self.settings)
        if line is not None:
            tr.write_line(line)

    @pytest.hookimpl
    def pytest_configure_node(self, node: object) -> None:
        """Send configuration to worker nodes."""
        node.workerinput["coverage_settings"] = self.settings.to_dict()  # type: ignore[attr-defined]

    @pytest.hookimpl
    def pytest_testnodedown(self, node: object, error: object) -> None:
        """Collect coverage data from finished worker."""
        worker_id = node.gateway.id  # type: ignore[attr-defined]
        if hasattr(node, "workeroutput") and "coverage_data" in node.workeroutput:  # type: ignore[attr-defined]
            self.worker_data[worker_id] = node.workeroutput["coverage_data"]  # type: ignore[attr-defined]

    @pytest.hookimpl
    def pytest_sessionfinish(self, session: Session, exitstatus: int) -> None:
        """Aggregate worker data and generate reports."""
        if self.settings.specs and self.orchestrator:
            # Multi-spec mode: merge per_spec dicts from each worker
            merged: dict[str, list[dict[str, Any]]] = {s.name: [] for s in self.settings.specs}
            for _worker_id, data in self.worker_data.items():
                if isinstance(data, dict) and "per_spec" in data:
                    for spec_name, interactions in data["per_spec"].items():
                        if spec_name in merged:
                            merged[spec_name].extend(interactions)
                    self.orchestrator.unmatched_count += data.get("unmatched_count", 0)

            # Feed merged per-spec interactions directly to reporters
            for spec_name, interactions in merged.items():
                reporter = self.orchestrator.reporters.get(spec_name)
                if reporter:
                    reporter.process_interactions(interactions)
            self.orchestrator.generate_all_reports()
        else:
            # Legacy path
            all_data: list[dict[str, Any]] = []
            for _worker_id, data in self.worker_data.items():
                if isinstance(data, list):
                    all_data.extend(data)
            if all_data and self.swagger_spec:
                self._generate_report(all_data)

    @pytest.hookimpl
    def pytest_terminal_summary(self, terminalreporter: TerminalReporter) -> None:
        """Print coverage summary to terminal."""
        if self.orchestrator:
            print_multi_spec_summary(terminalreporter, self.orchestrator)
        elif self.report_data:
            print_terminal_summary(terminalreporter, self.report_data, self.settings)
        elif self._swagger_load_error:
            terminalreporter.write_sep("=", "API Coverage Summary")
            terminalreporter.write_line(
                f"[api-coverage] No report generated — spec failed to load: {self._swagger_load_error}"
            )

    def _generate_report(self, data: list[dict[str, Any]]) -> None:
        """Generate coverage report from aggregated worker data."""
        if not self.swagger_spec:
            return

        reporter = CoverageReporter(
            self.swagger_spec,
            strip_prefixes=self.settings.strip_prefixes or None,
            split_by_origin=self.settings.split_by_origin,
        )
        reporter.process_interactions(data)
        self.report_data = reporter.generate_report()

        # Write reports to files
        written = write_reports(self.report_data, self.settings.output_dir, self.settings.formats)
        if written:
            logger.info("Reports written to: %s", self.settings.output_dir)


def _route_interaction_for_worker(interaction: dict[str, Any], specs: list[Any]) -> str | None:
    """Minimal routing for worker pre-filtering.

    Avoids importing MultiSpecOrchestrator on workers to keep them lightweight.
    """
    from urllib.parse import urlparse  # noqa: PLC0415

    from pytest_api_coverage.utils import normalize_origin  # noqa: PLC0415

    url = interaction.get("request", {}).get("url", "")
    req_origin = normalize_origin(url)

    for spec in specs:
        for spec_url in spec.api_urls:
            spec_origin = normalize_origin(spec_url)
            if req_origin != spec_origin:
                continue
            parsed_spec = urlparse(spec_url)
            parsed_req = urlparse(url)
            spec_path = (parsed_spec.path or "/").rstrip("/")
            req_path = parsed_req.path or "/"
            if req_path == parsed_spec.path or req_path.startswith(spec_path + "/"):
                return spec.name
    return None


class CoverageWorkerPlugin(_InterceptionMixin):
    """Coverage plugin for xdist worker nodes."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.collector = CoverageCollector()
        self.settings = CoverageSettings.from_dict(config.workerinput.get("coverage_settings", {}))  # type: ignore[attr-defined]
        self._adapters = [cls(self.collector) for cls in ADAPTER_REGISTRY]

    @pytest.hookimpl
    def pytest_sessionstart(self, session: Session) -> None:
        """Setup HTTP interception on worker."""
        self.settings.raise_if_error()  # raise deferred config errors here
        self._setup_http_interception()

    @pytest.hookimpl
    def pytest_sessionfinish(self, session: Session, exitstatus: int) -> None:
        """Send collected data back to master."""
        if self.settings.specs:
            per_spec: dict[str, list[dict[str, Any]]] = {s.name: [] for s in self.settings.specs}
            unmatched_count = 0
            for interaction in self.collector.get_data():
                spec_name = _route_interaction_for_worker(interaction, self.settings.specs)
                if spec_name and spec_name in per_spec:
                    per_spec[spec_name].append(interaction)
                else:
                    unmatched_count += 1
            session.config.workeroutput["coverage_data"] = {  # type: ignore[attr-defined]
                "per_spec": per_spec,
                "unmatched_count": unmatched_count,
            }
        else:
            session.config.workeroutput["coverage_data"] = self.collector.get_data()  # type: ignore[attr-defined]

    @pytest.hookimpl
    def pytest_unconfigure(self, config: Config) -> None:
        """Clean up adapters when worker finishes."""
        self._teardown_http_interception()
