"""Pytest plugin entry point with HTTP monkeypatching."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from pytest_api_coverage.adapters import ADAPTER_REGISTRY
from pytest_api_coverage.collector import CoverageCollector
from pytest_api_coverage.config.settings import CoverageSettings
from pytest_api_coverage.reporter import CoverageReporter
from pytest_api_coverage.schemas import SwaggerParser, SwaggerSpec
from pytest_api_coverage.writers import write_reports

if TYPE_CHECKING:
    from pytest import Config, Item, Parser, Session, TerminalReporter


def pytest_addoption(parser: Parser) -> None:
    """Add CLI options for API coverage."""
    group = parser.getgroup("api-coverage")
    group.addoption(
        "--swagger",
        dest="swagger",
        type=str,
        default=None,
        help="Path to swagger.json/yaml file or URL to swagger spec",
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
        "--coverage-base-url",
        dest="coverage_base_url",
        type=str,
        default=None,
        help="Filter coverage to single base URL (origin). Example: https://api.example.com",
    )
    group.addoption(
        "--coverage-include-base-url",
        dest="coverage_include_base_url",
        type=str,
        default=None,
        help="Allowlist of base URLs (comma-separated). Example: https://api.com,https://proxy.com",
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
        help="Name for a single spec (used with --coverage-spec-path or --coverage-spec-url)",
    )
    group.addoption(
        "--coverage-spec-path",
        dest="coverage_spec_path",
        type=str,
        default=None,
        help="Local file path to an OpenAPI spec for single-spec CLI mode",
    )
    group.addoption(
        "--coverage-spec-url",
        dest="coverage_spec_url",
        type=str,
        default=None,
        help="Remote URL of an OpenAPI spec for single-spec CLI mode",
    )
    group.addoption(
        "--coverage-spec-base-url",
        dest="coverage_spec_base_url",
        action="append",
        default=None,
        help="Base URL(s) for the spec (repeatable). Example: --coverage-spec-base-url https://api.example.com",
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


class CoverageSinglePlugin:
    """Coverage plugin for single-process test execution."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.settings = CoverageSettings.from_pytest_config(config)
        self.collector = CoverageCollector()
        self._adapters = [cls(self.collector) for cls in ADAPTER_REGISTRY]
        self.swagger_spec: SwaggerSpec | None = None
        self.report_data: dict[str, Any] | None = None

    @pytest.hookimpl
    def pytest_sessionstart(self, session: Session) -> None:
        """Setup HTTP interception at session start."""
        self._load_swagger()
        self._setup_http_interception()

    @pytest.hookimpl
    def pytest_runtest_setup(self, item: Item) -> None:
        """Set current test name before test runs."""
        self.collector.set_current_test(item.nodeid)

    @pytest.hookimpl
    def pytest_runtest_teardown(self, item: Item) -> None:
        """Clear current test name after test completes."""
        self.collector.set_current_test(None)

    @pytest.hookimpl
    def pytest_sessionfinish(self, session: Session, exitstatus: int) -> None:
        """Generate coverage reports at session end."""
        if self.collector.has_data() and self.swagger_spec:
            self._generate_report()

    @pytest.hookimpl
    def pytest_terminal_summary(self, terminalreporter: TerminalReporter) -> None:
        """Print coverage summary to terminal."""
        if self.report_data:
            _print_terminal_summary(terminalreporter, self.report_data)

    @pytest.hookimpl
    def pytest_unconfigure(self, config: Config) -> None:
        """Clean up adapters when pytest finishes."""
        self._teardown_http_interception()

    def _load_swagger(self) -> None:
        """Load and parse swagger specification."""
        try:
            self.swagger_spec = SwaggerParser.parse(self.settings.swagger)
        except Exception as e:
            print(f"\n[api-coverage] Warning: Failed to load swagger: {e}")

    def _setup_http_interception(self) -> None:
        """Install HTTP adapters for requests and httpx."""
        for adapter in self._adapters:
            adapter.install()

    def _teardown_http_interception(self) -> None:
        """Uninstall HTTP adapters to prevent memory leaks."""
        for adapter in self._adapters:
            adapter.uninstall()

    def _generate_report(self) -> None:
        """Generate coverage report using reporter."""
        if not self.swagger_spec:
            return

        reporter = CoverageReporter(
            self.swagger_spec,
            base_url=self.settings.base_url,
            include_base_urls=self.settings.include_base_urls or None,
            strip_prefixes=self.settings.strip_prefixes or None,
            split_by_origin=self.settings.split_by_origin,
        )
        reporter.process_interactions(self.collector.get_data())
        self.report_data = reporter.generate_report()

        # Write reports to files
        written = write_reports(self.report_data, self.settings.output_dir, self.settings.formats)
        if written:
            print(f"\n[api-coverage] Reports written to: {self.settings.output_dir}")


class CoverageMasterPlugin:
    """Coverage plugin for xdist master node."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.settings = CoverageSettings.from_pytest_config(config)
        self.worker_data: dict[str, list[dict[str, Any]]] = {}
        self.swagger_spec: SwaggerSpec | None = None
        self.report_data: dict[str, Any] | None = None

        # Load swagger on master
        self._load_swagger()

    def _load_swagger(self) -> None:
        """Load and parse swagger specification."""
        try:
            self.swagger_spec = SwaggerParser.parse(self.settings.swagger)
        except Exception as e:
            print(f"\n[api-coverage] Warning: Failed to load swagger: {e}")

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
        all_data: list[dict[str, Any]] = []
        for _worker_id, data in self.worker_data.items():
            all_data.extend(data)

        if all_data and self.swagger_spec:
            self._generate_report(all_data)

    @pytest.hookimpl
    def pytest_terminal_summary(self, terminalreporter: TerminalReporter) -> None:
        """Print coverage summary to terminal."""
        if self.report_data:
            _print_terminal_summary(terminalreporter, self.report_data)

    def _generate_report(self, data: list[dict[str, Any]]) -> None:
        """Generate coverage report from aggregated worker data."""
        if not self.swagger_spec:
            return

        reporter = CoverageReporter(
            self.swagger_spec,
            base_url=self.settings.base_url,
            include_base_urls=self.settings.include_base_urls or None,
            strip_prefixes=self.settings.strip_prefixes or None,
            split_by_origin=self.settings.split_by_origin,
        )
        reporter.process_interactions(data)
        self.report_data = reporter.generate_report()

        # Write reports to files
        written = write_reports(self.report_data, self.settings.output_dir, self.settings.formats)
        if written:
            print(f"\n[api-coverage] Reports written to: {self.settings.output_dir}")


class CoverageWorkerPlugin:
    """Coverage plugin for xdist worker nodes."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.collector = CoverageCollector()
        self.settings = CoverageSettings.from_dict(config.workerinput.get("coverage_settings", {}))  # type: ignore[attr-defined]
        self._adapters = [cls(self.collector) for cls in ADAPTER_REGISTRY]

    @pytest.hookimpl
    def pytest_sessionstart(self, session: Session) -> None:
        """Setup HTTP interception on worker."""
        self._setup_http_interception()

    @pytest.hookimpl
    def pytest_runtest_setup(self, item: Item) -> None:
        """Set current test name before test runs."""
        self.collector.set_current_test(item.nodeid)

    @pytest.hookimpl
    def pytest_runtest_teardown(self, item: Item) -> None:
        """Clear current test name after test completes."""
        self.collector.set_current_test(None)

    @pytest.hookimpl
    def pytest_sessionfinish(self, session: Session, exitstatus: int) -> None:
        """Send collected data back to master."""
        session.config.workeroutput["coverage_data"] = self.collector.get_data()  # type: ignore[attr-defined]

    @pytest.hookimpl
    def pytest_unconfigure(self, config: Config) -> None:
        """Clean up adapters when worker finishes."""
        self._teardown_http_interception()

    def _setup_http_interception(self) -> None:
        """Install HTTP adapters."""
        for adapter in self._adapters:
            adapter.install()

    def _teardown_http_interception(self) -> None:
        """Uninstall HTTP adapters."""
        for adapter in self._adapters:
            adapter.uninstall()


def _print_terminal_summary(terminalreporter: TerminalReporter, report_data: dict[str, Any]) -> None:
    """Print coverage summary to pytest terminal.

    Args:
        terminalreporter: pytest TerminalReporter
        report_data: Coverage report data
    """
    terminalreporter.write_sep("=", "API Coverage Summary")

    if report_data.get("split_by_origin"):
        _print_split_summary(terminalreporter, report_data)
    else:
        _print_standard_summary(terminalreporter, report_data)


def _print_standard_summary(terminalreporter: TerminalReporter, report_data: dict[str, Any]) -> None:
    """Print standard (non-split) coverage summary."""
    summary = report_data.get("summary", {})

    terminalreporter.write_line(
        f"Endpoints: {summary.get('covered_endpoints', 0)}/{summary.get('total_endpoints', 0)} covered "
        f"({summary.get('coverage_percentage', 0):.1f}%)"
    )
    terminalreporter.write_line(f"Total HTTP requests: {summary.get('total_requests', 0)}")

    # Show uncovered endpoints (grouped by path)
    endpoints = report_data.get("endpoints", [])
    uncovered_paths = [ep for ep in endpoints if not ep.get("is_covered", False)]
    if uncovered_paths:
        # Count total uncovered methods
        uncovered_methods = []
        for path_data in uncovered_paths:
            path = path_data.get("path", "")
            for method_data in path_data.get("methods", []):
                if not method_data.get("is_covered", False):
                    uncovered_methods.append((method_data.get("method", "?"), path))

        terminalreporter.write_line("")
        terminalreporter.write_line(f"Uncovered endpoints ({len(uncovered_methods)}):")
        for method, path in uncovered_methods[:10]:  # Show max 10
            terminalreporter.write_line(f"  - {method} {path}")
        if len(uncovered_methods) > 10:
            terminalreporter.write_line(f"  ... and {len(uncovered_methods) - 10} more")


def _print_split_summary(terminalreporter: TerminalReporter, report_data: dict[str, Any]) -> None:
    """Print split-by-origin coverage summary."""
    combined = report_data.get("combined_summary", {})
    origins = report_data.get("origins", {})

    terminalreporter.write_line(
        f"Combined: {combined.get('covered_endpoints', 0)}/{combined.get('total_endpoints', 0)} covered "
        f"({combined.get('coverage_percentage', 0):.1f}%)"
    )
    terminalreporter.write_line(f"Total HTTP requests: {combined.get('total_requests', 0)}")
    terminalreporter.write_line(f"Origins: {combined.get('origins_count', 0)}")

    # Show per-origin summaries
    for origin, origin_data in sorted(origins.items()):
        summary = origin_data.get("summary", {})
        terminalreporter.write_line("")
        terminalreporter.write_line(f"  {origin}:")
        terminalreporter.write_line(
            f"    {summary.get('covered_endpoints', 0)}/{summary.get('total_endpoints', 0)} covered "
            f"({summary.get('coverage_percentage', 0):.1f}%), "
            f"{summary.get('total_requests', 0)} requests"
        )
