"""Terminal output helpers for pytest-api-coverage."""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pytest import TerminalReporter

    from pytest_api_coverage.config.settings import CoverageSettings
    from pytest_api_coverage.orchestrator import MultiSpecOrchestrator


def print_terminal_summary(
    terminalreporter: TerminalReporter,
    report_data: dict[str, Any],
    settings: CoverageSettings,
    record_errors: int = 0,
) -> None:
    """Print coverage summary to pytest terminal (single-spec / --swagger mode).

    Uses unified table format: one row with spec name, endpoints, %, req count, filename.

    Args:
        terminalreporter: pytest TerminalReporter
        report_data: Coverage report data
        settings: Coverage settings (used to determine output path)
    """
    if report_data.get("split_by_origin"):
        print_split_summary(terminalreporter, report_data)
        return

    summary = report_data.get("summary", {})
    spec_name = pathlib.Path(str(report_data.get("swagger_source", "coverage"))).stem
    terminalreporter.write_sep("=", "API Coverage Summary")

    # Build file reference based on actual requested formats
    if "html" in settings.formats:
        file_ref = str(settings.output_dir / "coverage.html")
    elif "json" in settings.formats:
        file_ref = str(settings.output_dir / "coverage.json")
    elif "csv" in settings.formats:
        file_ref = str(settings.output_dir / "coverage.csv")
    else:
        file_ref = str(settings.output_dir)

    terminalreporter.write_line(
        f"{spec_name}   {summary.get('covered_endpoints', 0)}/{summary.get('total_endpoints', 0)} endpoints"
        f"   {summary.get('coverage_percentage', 0.0):.1f}%   {summary.get('total_requests', 0)} req"
        f"   {file_ref}"
    )
    unmatched = report_data.get("summary", {}).get("unmatched_requests", 0)
    if unmatched > 0:
        terminalreporter.write_line(
            f"[api-coverage] {unmatched} request(s) did not match any endpoint in the spec"
        )
    if record_errors > 0:
        terminalreporter.write_line(
            f"[api-coverage] Warning: {record_errors} HTTP recording error(s) — enable DEBUG logging for details",
            yellow=True,
        )


def print_multi_spec_summary(
    terminalreporter: TerminalReporter,
    orchestrator: MultiSpecOrchestrator,
    record_errors: int = 0,
    failed_specs: list[tuple[str, str]] | None = None,
) -> None:
    """Print multi-spec coverage summary to pytest terminal.

    Shows one row per spec with endpoints, %, req count, filename, plus a TOTAL row.
    If ``failed_specs`` is provided, failed spec load errors are printed before the
    table (or instead of it when no specs loaded successfully).

    Args:
        terminalreporter: pytest TerminalReporter
        orchestrator: MultiSpecOrchestrator with all spec reporters
        record_errors: Number of HTTP recording errors encountered during the session.
        failed_specs: Optional list of (spec_name, error_message) pairs for specs
            that could not be loaded.
    """
    specs = orchestrator.specs
    reporters = orchestrator.reporters
    if failed_specs:
        terminalreporter.write_sep("=", "API Coverage Summary")
        for name, error in failed_specs:
            terminalreporter.write_line(f"[api-coverage] FAILED to load spec '{name}': {error}")
        if not specs:
            return
    elif not specs:
        return

    rows = []
    for spec in specs:
        reporter = reporters.get(spec.name)
        if reporter is None:
            continue
        summary = reporter.generate_report()["summary"]
        formats = orchestrator.settings.formats
        if "html" in formats:
            ext = "html"
        elif "json" in formats:
            ext = "json"
        elif "csv" in formats:
            ext = "csv"
        else:
            ext = "html"
        rows.append(
            {
                "name": spec.name,
                "covered": summary["covered_endpoints"],
                "total": summary["total_endpoints"],
                "pct": summary["coverage_percentage"],
                "requests": summary["total_requests"],
                "filename": f"{spec.name}-coverage.{ext}",
            }
        )

    n = len(specs)
    terminalreporter.write_sep("=", f"API Coverage Summary ({n} specs)")

    max_name_len = max((len(r["name"]) for r in rows), default=5)
    max_name_len = max(max_name_len, len("TOTAL"))

    for row in rows:
        name_col = row["name"].ljust(max_name_len)
        terminalreporter.write_line(
            f"{name_col}   {row['covered']}/{row['total']} endpoints"
            f"   {row['pct']:.1f}%   {row['requests']} req   {row['filename']}"
        )

    total_covered = sum(r["covered"] for r in rows)
    total_endpoints = sum(r["total"] for r in rows)
    total_pct = (total_covered / total_endpoints * 100) if total_endpoints > 0 else 0.0
    total_requests = sum(r["requests"] for r in rows)
    unmatched = orchestrator.unmatched_count
    name_col = "TOTAL".ljust(max_name_len)
    terminalreporter.write_line(
        f"{name_col}   {total_covered}/{total_endpoints} endpoints"
        f"   {total_pct:.1f}%   {total_requests} req   {unmatched} unmatched"
    )
    if record_errors > 0:
        terminalreporter.write_line(
            f"[api-coverage] Warning: {record_errors} HTTP recording error(s) — enable DEBUG logging for details",
            yellow=True,
        )


def print_split_summary(terminalreporter: TerminalReporter, report_data: dict[str, Any]) -> None:
    """Print split-by-origin coverage summary."""
    terminalreporter.write_sep("=", "API Coverage Summary")
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
