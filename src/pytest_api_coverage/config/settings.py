"""Configuration settings for API coverage plugin."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

# Module-level logger — placed after all imports to satisfy E402
logger = logging.getLogger("pytest_api_coverage")


@dataclass
class SpecConfig:
    """Per-spec configuration for multi-spec API coverage.

    Represents a single OpenAPI specification and its associated
    target URLs. Supports both local file paths and remote URLs
    for the spec source, with xdist-safe serialisation.
    """

    name: str
    api_urls: list[str]
    swagger_path: str | Path | None = None
    swagger_url: str | None = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.name:
            raise ValueError("SpecConfig 'name' must be a non-empty string")

        if self.swagger_path is not None and self.swagger_url is not None:
            raise ValueError("SpecConfig 'swagger_path' and 'swagger_url' are mutually exclusive; provide only one")

        if not self.api_urls:
            raise ValueError("SpecConfig 'api_urls' must be a non-empty list")

        # Normalise path to Path object
        if self.swagger_path is not None and isinstance(self.swagger_path, str):
            self.swagger_path = Path(self.swagger_path)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpecConfig:
        """Create SpecConfig from a dictionary.

        Args:
            data: Dictionary with spec configuration values.
                  Must contain 'name' and 'api_urls' keys.

        Returns:
            SpecConfig instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if "api_urls" not in data:
            raise ValueError("SpecConfig dict must contain 'api_urls' key")
        return cls(
            name=data["name"],
            api_urls=data["api_urls"],
            swagger_path=data.get("swagger_path"),
            swagger_url=data.get("swagger_url"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize SpecConfig to a JSON-safe dictionary.

        All values are JSON primitives (path serialised as str).
        Safe for xdist master-to-worker transfer via JSON.

        Returns:
            Dictionary with serializable values
        """
        return {
            "name": self.name,
            "api_urls": self.api_urls,
            "swagger_path": str(self.swagger_path) if self.swagger_path is not None else None,
            "swagger_url": self.swagger_url,
        }


@dataclass
class CoverageSettings:
    """Configuration settings for API coverage plugin.

    Can be initialized from:
    - pytest CLI options
    - Direct instantiation
    - Deserialization (for xdist workers)
    """

    spec: str | Path | None = None
    output_dir: Path = field(default_factory=lambda: Path("coverage-output"))
    formats: set[str] = field(default_factory=lambda: {"json", "csv", "html"})

    # Path normalization
    strip_prefixes: list[str] = field(default_factory=list)  # Manual prefixes to strip

    # Split by origin
    split_by_origin: bool = False  # Generate separate coverage per origin

    # Multi-spec support
    specs: list[SpecConfig] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate and normalize settings after initialization."""
        # Validate spec path/URL
        if self.spec is not None:
            self.spec = self._validate_spec(self.spec)

        # Ensure output_dir is a Path
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

        # Parse formats if string
        if isinstance(self.formats, str):
            self.formats = {f.strip().lower() for f in self.formats.split(",")}
        elif isinstance(self.formats, list | tuple):
            self.formats = set(self.formats)

        # Parse strip_prefixes if string
        if isinstance(self.strip_prefixes, str):
            self.strip_prefixes = [p.strip() for p in self.strip_prefixes.split(",") if p.strip()]

    @staticmethod
    def _validate_spec(value: str | Path) -> str | Path:
        """Validate spec source: file path or URL.

        Args:
            value: Spec path or URL

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
        coverage_spec = config.getoption("coverage_spec", None)

        # Read multi-spec CLI options
        spec_name = config.getoption("coverage_spec_name", None)
        spec_api_urls = config.getoption("coverage_spec_api_url", None) or []

        specs: list[SpecConfig] = []
        top_level: dict[str, Any] = {}

        if coverage_spec and spec_name:
            # --coverage-spec with --coverage-spec-name → multi-spec mode via CLI
            if not spec_api_urls:
                pytest.exit(
                    "[api-coverage] --coverage-spec-name requires --coverage-spec-api-url",
                    returncode=1,
                )
            else:
                spec_value = str(coverage_spec)
                swagger_url: str | None = None
                swagger_path: str | None = None
                if spec_value.startswith(("http://", "https://")):
                    swagger_url = spec_value
                else:
                    swagger_path = spec_value
                specs = [
                    SpecConfig(
                        name=spec_name,
                        api_urls=spec_api_urls,
                        swagger_path=swagger_path,
                        swagger_url=swagger_url,
                    )
                ]
                coverage_spec = None  # Use multi-spec path
        elif spec_name and not coverage_spec:
            pytest.exit(
                "[api-coverage] --coverage-spec-name requires --coverage-spec",
                returncode=1,
            )
        elif coverage_spec is None:
            from pytest_api_coverage.config.multi_spec import (  # noqa: PLC0415
                _discover_config_file,
                load_multi_spec_config,
            )

            explicit_config = config.getoption("coverage_config", None)

            if explicit_config:
                config_path = Path(explicit_config)
                if not config_path.exists():
                    pytest.exit(
                        f"[api-coverage] Config file not found: {config_path}",
                        returncode=1,
                    )
                specs, top_level = load_multi_spec_config(config_path)
            else:
                discovered = _discover_config_file(config.rootpath)
                if discovered:
                    specs, top_level = load_multi_spec_config(discovered)

            # Validate that each spec's path exists on disk
            for spec in specs:
                if spec.swagger_path and not Path(str(spec.swagger_path)).exists():
                    pytest.exit(
                        f"[api-coverage] Spec file not found: {spec.swagger_path} (spec: '{spec.name}')",
                        returncode=1,
                    )

        # Apply top-level config values; CLI options take precedence over config file.
        _default_output = "coverage-output"
        _default_formats = "json,csv,html"
        raw_output = config.getoption("coverage_output", _default_output)
        raw_formats = config.getoption("coverage_format", _default_formats)

        effective_output = raw_output
        if raw_output == _default_output and "output_dir" in top_level:
            effective_output = top_level["output_dir"]

        effective_formats = raw_formats
        if raw_formats == _default_formats and "formats" in top_level:
            effective_formats = top_level["formats"]

        return cls(
            spec=coverage_spec,
            output_dir=Path(effective_output),
            formats=effective_formats,
            strip_prefixes=config.getoption("coverage_strip_prefix", None) or "",  # type: ignore[arg-type]
            split_by_origin=config.getoption("coverage_split_by_origin", False),
            specs=specs,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CoverageSettings:
        """Create settings from dictionary (for xdist worker deserialization).

        Args:
            data: Dictionary with settings values

        Returns:
            CoverageSettings instance
        """
        spec = data.get("spec")
        if spec and not str(spec).startswith(("http://", "https://")):
            spec = Path(spec)

        output_dir = data.get("output_dir", "coverage-output")
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)

        raw_formats = data.get("formats", {"json", "csv", "html"})
        if isinstance(raw_formats, (list, set)):
            formats: set[str] = {str(f) for f in raw_formats}
        else:
            formats = {"json", "csv", "html"}

        specs = [SpecConfig.from_dict(s) for s in data.get("specs", [])]

        return cls(
            spec=spec,
            output_dir=output_dir,
            formats=formats,
            strip_prefixes=data.get("strip_prefixes", []),
            split_by_origin=data.get("split_by_origin", False),
            specs=specs,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize settings to dictionary (for xdist master-to-worker transfer).

        Returns:
            Dictionary with serializable values
        """
        return {
            "spec": str(self.spec) if self.spec else None,
            "output_dir": str(self.output_dir),
            "formats": list(self.formats),
            "strip_prefixes": self.strip_prefixes,
            "split_by_origin": self.split_by_origin,
            "specs": [s.to_dict() for s in self.specs],
        }

    def is_enabled(self) -> bool:
        """Check if coverage collection is enabled.

        Returns:
            True if spec is configured or specs list is non-empty
        """
        return self.spec is not None or bool(self.specs)
