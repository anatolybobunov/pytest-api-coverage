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


def print_multi_spec_summary(terminalreporter: TerminalReporter, orchestrator: MultiSpecOrchestrator) -> None:
    """Print multi-spec coverage summary to pytest terminal.

    Shows one row per spec with endpoints, %, req count, filename, plus a TOTAL row.

    Args:
        terminalreporter: pytest TerminalReporter
        orchestrator: MultiSpecOrchestrator with all spec reporters
    """
    specs = orchestrator.specs
    reporters = orchestrator.reporters
    if not specs:
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
