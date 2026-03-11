"""Report writers for JSON, CSV, HTML formats."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pytest_api_coverage.writers.csv_writer import CsvWriter
from pytest_api_coverage.writers.html_writer import HtmlWriter
from pytest_api_coverage.writers.json_writer import JsonWriter

__all__ = ["JsonWriter", "CsvWriter", "HtmlWriter", "write_reports"]


def write_reports(
    report_data: dict[str, Any],
    output_dir: str | Path,
    formats: set[str],
    prefix: str | None = None,
) -> list[Path]:
    """Write coverage reports in specified formats.

    Args:
        report_data: Coverage report data dict
        output_dir: Directory for output files
        formats: Set of format names (json, csv, html)
        prefix: Optional prefix for output filenames. When set, produces
            ``{prefix}-coverage.{ext}`` files. When None, produces
            ``coverage.{ext}`` files (default, backward-compatible behaviour).

    Returns:
        List of paths to written files
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = f"{prefix}-coverage" if prefix else "coverage"
    written_files: list[Path] = []

    if "json" in formats:
        written_files.append(JsonWriter.write(report_data, output_dir / f"{stem}.json"))

    if "csv" in formats:
        written_files.append(CsvWriter.write(report_data, output_dir / f"{stem}.csv"))

    if "html" in formats:
        written_files.append(HtmlWriter.write(report_data, output_dir / f"{stem}.html"))

    return written_files
