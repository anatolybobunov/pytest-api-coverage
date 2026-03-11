"""CSV report writer."""

from __future__ import annotations

import csv
import io
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


class CsvWriter:
    """Writes coverage report as CSV file."""

    @classmethod
    def write(cls, report_data: dict[str, Any], output_path: str | Path) -> Path:
        """Write endpoint coverage data to CSV file.

        Args:
            report_data: Coverage report dictionary
            output_path: Destination file path

        Returns:
            Path to written file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames, rows = cls._build_rows(report_data)

        # Atomic write
        fd, temp_path = tempfile.mkstemp(
            suffix=".csv",
            dir=output_path.parent,
        )
        os.close(fd)

        try:
            with open(temp_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
                writer.writeheader()
                writer.writerows(rows)
            shutil.move(temp_path, output_path)
        except Exception:
            Path(temp_path).unlink(missing_ok=True)
            raise

        return output_path

    @classmethod
    def _build_rows(cls, report_data: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
        """Convert report data to (fieldnames, rows) for CSV serialisation.

        Args:
            report_data: Coverage report dictionary

        Returns:
            Tuple of column headers and list of row dicts
        """
        if report_data.get("split_by_origin"):
            return cls._to_rows_split(report_data)
        return cls._to_rows_standard(report_data)

    @classmethod
    def _to_rows_standard(cls, report_data: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
        """Convert standard report to (fieldnames, rows) grouped by path."""
        fieldnames: list[str] = ["Path", "Hit Count", "Method", "Method Count", "Response Codes", "Covered"]
        endpoints = report_data.get("endpoints", [])
        swagger_source = report_data.get("swagger_source", "")

        rows: list[dict[str, Any]] = []

        # Add swagger source header row
        if swagger_source:
            rows.append(
                {
                    "Path": "SWAGGER",
                    "Hit Count": swagger_source,
                    "Method": "",
                    "Method Count": "",
                    "Response Codes": "",
                    "Covered": "",
                }
            )

        for path_data in endpoints:
            rows.extend(cls._path_to_rows(path_data))

        # Add summary row
        summary = report_data.get("summary", {})
        rows.append(
            {
                "Path": "TOTAL",
                "Hit Count": summary.get("total_requests", 0),
                "Method": "",
                "Method Count": f"{summary.get('covered_endpoints', 0)}/{summary.get('total_endpoints', 0)} endpoints",
                "Response Codes": "",
                "Covered": f"{summary.get('coverage_percentage', 0):.1f}%",
            }
        )

        return fieldnames, rows

    @classmethod
    def _to_rows_split(cls, report_data: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
        """Convert split-by-origin report to (fieldnames, rows) grouped by path."""
        fieldnames: list[str] = [
            "Origin",
            "Path",
            "Hit Count",
            "Method",
            "Method Count",
            "Response Codes",
            "Covered",
        ]
        origins = report_data.get("origins", {})
        swagger_source = report_data.get("swagger_source", "")

        rows: list[dict[str, Any]] = []

        # Add swagger source header row
        if swagger_source:
            rows.append(
                {
                    "Origin": "SWAGGER",
                    "Path": swagger_source,
                    "Hit Count": "",
                    "Method": "",
                    "Method Count": "",
                    "Response Codes": "",
                    "Covered": "",
                }
            )

        for origin, origin_data in sorted(origins.items()):
            endpoints = origin_data.get("endpoints", [])
            for path_data in endpoints:
                for row in cls._path_to_rows(path_data):
                    row["Origin"] = origin
                    rows.append(row)

            # Add origin summary row
            summary = origin_data.get("summary", {})
            rows.append(
                {
                    "Origin": origin,
                    "Path": "SUBTOTAL",
                    "Hit Count": summary.get("total_requests", 0),
                    "Method": "",
                    "Method Count": (
                        f"{summary.get('covered_endpoints', 0)}/{summary.get('total_endpoints', 0)} endpoints"
                    ),
                    "Response Codes": "",
                    "Covered": f"{summary.get('coverage_percentage', 0):.1f}%",
                }
            )

        # Add combined summary row
        combined = report_data.get("combined_summary", {})
        rows.append(
            {
                "Origin": "ALL",
                "Path": "TOTAL",
                "Hit Count": combined.get("total_requests", 0),
                "Method": "",
                "Method Count": (
                    f"{combined.get('covered_endpoints', 0)}/{combined.get('total_endpoints', 0)} endpoints"
                ),
                "Response Codes": "",
                "Covered": f"{combined.get('coverage_percentage', 0):.1f}%",
            }
        )

        return fieldnames, rows

    @classmethod
    def _path_to_rows(cls, path_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Convert grouped path data to CSV rows."""
        rows: list[dict[str, Any]] = []
        path = path_data["path"]
        total_hit_count = path_data["hit_count"]
        methods = path_data.get("methods", [])

        for i, method_data in enumerate(methods):
            response_codes = method_data.get("response_codes", {})
            if isinstance(response_codes, dict):
                codes_str = ", ".join(f"{code}({count})" for code, count in sorted(response_codes.items()))
            else:
                codes_str = ", ".join(map(str, response_codes))

            rows.append(
                {
                    "Path": path if i == 0 else "",  # Path only in first row
                    "Hit Count": total_hit_count if i == 0 else "",  # Total only in first
                    "Method": method_data["method"],
                    "Method Count": method_data["hit_count"],
                    "Response Codes": codes_str,
                    "Covered": "Yes" if method_data["is_covered"] else "No",
                }
            )

        return rows

    @classmethod
    def write_string(cls, report_data: dict[str, Any]) -> str:
        """Serialize report data to CSV string.

        Args:
            report_data: Coverage report dictionary

        Returns:
            CSV string
        """
        fieldnames, rows = cls._build_rows(report_data)
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()
