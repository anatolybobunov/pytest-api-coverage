"""Report writers for JSON, CSV, HTML formats."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from pytest_api_coverage.writers.csv_writer import CsvWriter
from pytest_api_coverage.writers.html_writer import HtmlWriter
from pytest_api_coverage.writers.json_writer import JsonWriter

__all__ = ["JsonWriter", "CsvWriter", "HtmlWriter", "WriterProtocol", "WRITER_REGISTRY", "write_reports"]


class WriterProtocol(Protocol):
    """Protocol for report writer classes."""

    @classmethod
    def write(cls, report_data: dict[str, Any], output_path: str | Path) -> Path:
        """Write report data to a file.

        Args:
            report_data: Coverage report data dict
            output_path: Destination file path

        Returns:
            Path to written file
        """
        ...


WRITER_REGISTRY: dict[str, type[WriterProtocol]] = {
    "json": JsonWriter,
    "csv": CsvWriter,
    "html": HtmlWriter,
}


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

    for fmt in formats:
        if fmt in WRITER_REGISTRY:
            writer_cls = WRITER_REGISTRY[fmt]
            written_files.append(writer_cls.write(report_data, output_dir / f"{stem}.{fmt}"))

    return written_files
