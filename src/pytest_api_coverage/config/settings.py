"""Configuration settings for API coverage plugin."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pytest


@dataclass
class CoverageSettings:
    """Configuration settings for API coverage plugin.

    Can be initialized from:
    - pytest CLI options
    - Direct instantiation
    - Deserialization (for xdist workers)
    """

    swagger: str | Path | None = None
    output_dir: Path = field(default_factory=lambda: Path("coverage-output"))
    formats: set[str] = field(default_factory=lambda: {"json", "csv", "html"})

    # Origin filtering
    base_url: str | None = None  # Single origin filter
    include_base_urls: set[str] = field(default_factory=set)  # Allowlist of origins

    # Path normalization
    strip_prefixes: list[str] = field(default_factory=list)  # Manual prefixes to strip

    # Split by origin
    split_by_origin: bool = False  # Generate separate coverage per origin

    def __post_init__(self) -> None:
        """Validate and normalize settings after initialization."""
        # Validate swagger path/URL
        if self.swagger is not None:
            self.swagger = self._validate_swagger(self.swagger)

        # Ensure output_dir is a Path
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

        # Parse formats if string
        if isinstance(self.formats, str):
            self.formats = {f.strip().lower() for f in self.formats.split(",")}
        elif isinstance(self.formats, list | tuple):
            self.formats = set(self.formats)

        # Parse include_base_urls if string
        if isinstance(self.include_base_urls, str):
            self.include_base_urls = {u.strip() for u in self.include_base_urls.split(",") if u.strip()}
        elif isinstance(self.include_base_urls, list | tuple):
            self.include_base_urls = set(self.include_base_urls)

        # Parse strip_prefixes if string
        if isinstance(self.strip_prefixes, str):
            self.strip_prefixes = [p.strip() for p in self.strip_prefixes.split(",") if p.strip()]

    @staticmethod
    def _validate_swagger(value: str | Path) -> str | Path:
        """Validate swagger source: file path or URL.

        Args:
            value: Swagger path or URL

        Returns:
            Validated path or URL string

        Raises:
            ValueError: If local file doesn't exist
        """
        value_str = str(value)

        # Support URL sources (pass through for later fetching)
        if value_str.startswith(("http://", "https://")):
            return value_str

        # Local file path - validate existence
        path = Path(value_str)
        if not path.exists():
            raise ValueError(f"Swagger file not found: {path}")
        return path

    @classmethod
    def from_pytest_config(cls, config: pytest.Config) -> CoverageSettings:
        """Create settings from pytest configuration.

        Args:
            config: pytest Config object with parsed CLI options

        Returns:
            CoverageSettings instance
        """
        return cls(
            swagger=config.getoption("swagger", None),
            output_dir=Path(config.getoption("coverage_output", "coverage-output")),
            formats=config.getoption("coverage_format", "json,csv,html"),
            base_url=config.getoption("coverage_base_url", None),
            include_base_urls=config.getoption("coverage_include_base_url", None) or "",
            strip_prefixes=config.getoption("coverage_strip_prefix", None) or "",
            split_by_origin=config.getoption("coverage_split_by_origin", False),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CoverageSettings:
        """Create settings from dictionary (for xdist worker deserialization).

        Args:
            data: Dictionary with settings values

        Returns:
            CoverageSettings instance
        """
        swagger = data.get("swagger")
        if swagger and not str(swagger).startswith(("http://", "https://")):
            swagger = Path(swagger)

        output_dir = data.get("output_dir", "coverage-output")
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)

        formats = data.get("formats", {"json", "csv", "html"})
        if isinstance(formats, list):
            formats = set(formats)

        include_base_urls = data.get("include_base_urls", set())
        if isinstance(include_base_urls, list):
            include_base_urls = set(include_base_urls)

        return cls(
            swagger=swagger,
            output_dir=output_dir,
            formats=formats,
            base_url=data.get("base_url"),
            include_base_urls=include_base_urls,
            strip_prefixes=data.get("strip_prefixes", []),
            split_by_origin=data.get("split_by_origin", False),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize settings to dictionary (for xdist master-to-worker transfer).

        Returns:
            Dictionary with serializable values
        """
        return {
            "swagger": str(self.swagger) if self.swagger else None,
            "output_dir": str(self.output_dir),
            "formats": list(self.formats),
            "base_url": self.base_url,
            "include_base_urls": list(self.include_base_urls),
            "strip_prefixes": self.strip_prefixes,
            "split_by_origin": self.split_by_origin,
        }

    def is_enabled(self) -> bool:
        """Check if coverage collection is enabled.

        Returns:
            True if swagger is configured
        """
        return self.swagger is not None
