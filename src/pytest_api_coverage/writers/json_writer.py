"""JSON report writer."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class JsonWriter:
    """Writes coverage report as JSON file."""

    @classmethod
    def write(cls, report_data: dict[str, Any], output_path: str | Path) -> Path:
        """Write report data to JSON file with atomic write.

        Args:
            report_data: Coverage report dictionary
            output_path: Destination file path

        Returns:
            Path to written file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Add metadata (swagger_source first for visibility)
        output_data = {
            "format_version": "1.0",
            "generated_at": datetime.now(UTC).isoformat(),
            "swagger_source": report_data.get("swagger_source", ""),
            **{k: v for k, v in report_data.items() if k != "swagger_source"},
        }

        # Atomic write: write to temp file, then rename
        fd, temp_path = tempfile.mkstemp(
            suffix=".json",
            dir=output_path.parent,
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)

            # Atomic rename
            shutil.move(temp_path, output_path)
        except Exception:
            # Clean up temp file on error
            Path(temp_path).unlink(missing_ok=True)
            raise

        return output_path

    @classmethod
    def write_string(cls, report_data: dict[str, Any]) -> str:
        """Serialize report data to JSON string.

        Args:
            report_data: Coverage report dictionary

        Returns:
            JSON string
        """
        output_data = {
            "format_version": "1.0",
            "generated_at": datetime.now(UTC).isoformat(),
            "swagger_source": report_data.get("swagger_source", ""),
            **{k: v for k, v in report_data.items() if k != "swagger_source"},
        }
        return json.dumps(output_data, indent=2, ensure_ascii=False, default=str)
