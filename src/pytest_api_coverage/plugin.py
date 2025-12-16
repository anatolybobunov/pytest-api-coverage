"""Pytest plugin entry point with HTTP monkeypatching."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from pytest_api_coverage.adapters import HttpxAdapter, RequestsAdapter
from pytest_api_coverage.collector import CoverageCollector
from pytest_api_coverage.reporter import CoverageReporter
from pytest_api_coverage.schemas import SwaggerParser, SwaggerSpec

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


def pytest_configure(config: Config) -> None:
    """Register the appropriate plugin based on execution mode."""
    swagger = config.getoption("swagger", None)
    if not swagger:
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
        self.collector = CoverageCollector()
        self.swagger_path = config.getoption("swagger")
        self.output_dir = config.getoption("coverage_output")
        self.formats = set(config.getoption("coverage_format").split(","))
        self.swagger_spec: SwaggerSpec | None = None
        self.report_data: dict[str, Any] | None = None

        # Origin filtering options
        self.base_url = config.getoption("coverage_base_url")
        self.include_base_urls = self._parse_csv_option(config.getoption("coverage_include_base_url"))
        self.strip_prefixes = self._parse_csv_list(config.getoption("coverage_strip_prefix"))
        self.split_by_origin = config.getoption("coverage_split_by_origin")

    @staticmethod
    def _parse_csv_option(value: str | None) -> set[str]:
        """Parse comma-separated string into set."""
        if not value:
            return set()
        return {v.strip() for v in value.split(",") if v.strip()}

    @staticmethod
    def _parse_csv_list(value: str | None) -> list[str]:
        """Parse comma-separated string into list."""
        if not value:
            return []
        return [v.strip() for v in value.split(",") if v.strip()]

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
            self.swagger_spec = SwaggerParser.parse(self.swagger_path)
        except Exception as e:
            print(f"\n[api-coverage] Warning: Failed to load swagger: {e}")

    def _setup_http_interception(self) -> None:
        """Install HTTP adapters for requests and httpx."""
        RequestsAdapter.install(self.collector)
        HttpxAdapter.install(self.collector)

    def _teardown_http_interception(self) -> None:
        """Uninstall HTTP adapters to prevent memory leaks."""
        RequestsAdapter.uninstall()
        HttpxAdapter.uninstall()

    def _generate_report(self) -> None:
        """Generate coverage report using reporter."""
        if not self.swagger_spec:
            return

        reporter = CoverageReporter(
            self.swagger_spec,
            base_url=self.base_url,
            include_base_urls=self.include_base_urls or None,
            strip_prefixes=self.strip_prefixes or None,
            split_by_origin=self.split_by_origin,
        )
        reporter.process_interactions(self.collector.get_data())
        self.report_data = reporter.generate_report()

        # Write reports to files
        output_dir = Path(self.output_dir)
        written = reporter.write_reports(output_dir, self.formats)
        if written:
            print(f"\n[api-coverage] Reports written to: {output_dir}")


class CoverageMasterPlugin:
    """Coverage plugin for xdist master node."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.swagger_path = config.getoption("swagger")
        self.output_dir = config.getoption("coverage_output")
        self.formats = set(config.getoption("coverage_format").split(","))
        self.worker_data: dict[str, list[dict[str, Any]]] = {}
        self.swagger_spec: SwaggerSpec | None = None
        self.report_data: dict[str, Any] | None = None

        # Origin filtering options
        self.base_url = config.getoption("coverage_base_url")
        self.include_base_urls = self._parse_csv_option(config.getoption("coverage_include_base_url"))
        self.strip_prefixes = self._parse_csv_list(config.getoption("coverage_strip_prefix"))
        self.split_by_origin = config.getoption("coverage_split_by_origin")

        # Load swagger on master
        self._load_swagger()

    @staticmethod
    def _parse_csv_option(value: str | None) -> set[str]:
        """Parse comma-separated string into set."""
        if not value:
            return set()
        return {v.strip() for v in value.split(",") if v.strip()}

    @staticmethod
    def _parse_csv_list(value: str | None) -> list[str]:
        """Parse comma-separated string into list."""
        if not value:
            return []
        return [v.strip() for v in value.split(",") if v.strip()]

    def _load_swagger(self) -> None:
        """Load and parse swagger specification."""
        try:
            self.swagger_spec = SwaggerParser.parse(self.swagger_path)
        except Exception as e:
            print(f"\n[api-coverage] Warning: Failed to load swagger: {e}")

    @pytest.hookimpl
    def pytest_configure_node(self, node: object) -> None:
        """Send configuration to worker nodes."""
        # Pass settings to worker
        node.workerinput["coverage_swagger"] = self.swagger_path  # type: ignore[attr-defined]
        node.workerinput["coverage_output"] = self.output_dir  # type: ignore[attr-defined]
        node.workerinput["coverage_formats"] = ",".join(self.formats)  # type: ignore[attr-defined]

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
            base_url=self.base_url,
            include_base_urls=self.include_base_urls or None,
            strip_prefixes=self.strip_prefixes or None,
            split_by_origin=self.split_by_origin,
        )
        reporter.process_interactions(data)
        self.report_data = reporter.generate_report()

        # Write reports to files
        output_dir = Path(self.output_dir)
        written = reporter.write_reports(output_dir, self.formats)
        if written:
            print(f"\n[api-coverage] Reports written to: {output_dir}")


class CoverageWorkerPlugin:
    """Coverage plugin for xdist worker nodes."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.collector = CoverageCollector()
        # Get settings from master via workerinput
        self.swagger_path = config.workerinput.get("coverage_swagger")  # type: ignore[attr-defined]

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
        RequestsAdapter.install(self.collector)
        HttpxAdapter.install(self.collector)

    def _teardown_http_interception(self) -> None:
        """Uninstall HTTP adapters."""
        RequestsAdapter.uninstall()
        HttpxAdapter.uninstall()


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

    # Show uncovered endpoints
    endpoints = report_data.get("endpoints", [])
    uncovered = [ep for ep in endpoints if not ep.get("is_covered", False)]
    if uncovered:
        terminalreporter.write_line("")
        terminalreporter.write_line(f"Uncovered endpoints ({len(uncovered)}):")
        for ep in uncovered[:10]:  # Show max 10
            terminalreporter.write_line(f"  - {ep['method']} {ep['path']}")
        if len(uncovered) > 10:
            terminalreporter.write_line(f"  ... and {len(uncovered) - 10} more")


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
