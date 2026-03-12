"""Configuration settings for API coverage plugin."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pytest


@dataclass
class SpecConfig:
    """Per-spec configuration for multi-spec API coverage.

    Represents a single OpenAPI specification and its associated
    target URLs. Supports both local file paths and remote URLs
    for the spec source, with xdist-safe serialisation.
    """

    name: str
    urls: list[str]
    path: str | Path | None = None
    url: str | None = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.name:
            raise ValueError("SpecConfig 'name' must be a non-empty string")

        if self.path is not None and self.url is not None:
            raise ValueError("SpecConfig 'path' and 'url' are mutually exclusive; provide only one")

        if not self.urls:
            raise ValueError("SpecConfig 'urls' must be a non-empty list")

        # Normalise path to Path object
        if self.path is not None and isinstance(self.path, str):
            self.path = Path(self.path)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpecConfig:
        """Create SpecConfig from a dictionary.

        Args:
            data: Dictionary with spec configuration values.
                  Must contain 'name' and 'urls' keys.

        Returns:
            SpecConfig instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if "urls" not in data:
            raise ValueError("SpecConfig dict must contain 'urls' key")
        return cls(
            name=data["name"],
            urls=data["urls"],
            path=data.get("path"),
            url=data.get("url"),
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
            "urls": self.urls,
            "path": str(self.path) if self.path is not None else None,
            "url": self.url,
        }


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

    # Multi-spec support
    specs: list[SpecConfig] = field(default_factory=list)

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
        swagger = config.getoption("swagger", None)

        # Read multi-spec CLI options
        spec_name = config.getoption("coverage_spec_name", None)
        spec_path = config.getoption("coverage_spec_path", None)
        spec_url = config.getoption("coverage_spec_url", None)
        spec_base_urls = config.getoption("coverage_spec_base_url", None) or []

        specs: list[SpecConfig] = []
        top_level: dict[str, Any] = {}
        any_spec_flag = spec_name or spec_path or spec_url

        if swagger and any_spec_flag:
            # --swagger cannot be combined with multi-spec flags; swagger wins
            print("\n[api-coverage] Warning: --swagger cannot be combined with multi-spec flags; using --swagger mode")
        elif any_spec_flag:
            if not spec_name:
                print(
                    "\n[api-coverage] Warning: --coverage-spec-path/--coverage-spec-url requires "
                    "--coverage-spec-name; skipping spec"
                )
            elif not spec_base_urls:
                print("\n[api-coverage] Warning: --coverage-spec-name requires --coverage-spec-base-url")
            elif spec_path and spec_url:
                print(
                    "\n[api-coverage] Warning: --coverage-spec-path and --coverage-spec-url are "
                    "mutually exclusive; skipping spec"
                )
            else:
                specs = [
                    SpecConfig(
                        name=spec_name,
                        urls=spec_base_urls,
                        path=spec_path,
                        url=spec_url,
                    )
                ]
        elif swagger is None:
            from pytest_api_coverage.config.multi_spec import (  # noqa: PLC0415
                _discover_config_file,
                load_multi_spec_config,
            )

            explicit_config = config.getoption("coverage_config", None)

            if explicit_config:
                config_path = Path(explicit_config)
                if not config_path.exists():
                    import pytest as _pytest  # noqa: PLC0415

                    _pytest.exit(
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
                if spec.path and not Path(str(spec.path)).exists():
                    import pytest as _pytest  # noqa: PLC0415

                    _pytest.exit(
                        f"[api-coverage] Spec file not found: {spec.path} (spec: '{spec.name}')",
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
            swagger=swagger,
            output_dir=Path(effective_output),
            formats=effective_formats,
            base_url=config.getoption("coverage_base_url", None),
            include_base_urls=config.getoption("coverage_include_base_url", None) or "",  # type: ignore[arg-type]
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

        specs = [SpecConfig.from_dict(s) for s in data.get("specs", [])]

        return cls(
            swagger=swagger,
            output_dir=output_dir,
            formats=formats,
            base_url=data.get("base_url"),
            include_base_urls=include_base_urls,
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
            "swagger": str(self.swagger) if self.swagger else None,
            "output_dir": str(self.output_dir),
            "formats": list(self.formats),
            "base_url": self.base_url,
            "include_base_urls": list(self.include_base_urls),
            "strip_prefixes": self.strip_prefixes,
            "split_by_origin": self.split_by_origin,
            "specs": [s.to_dict() for s in self.specs],
        }

    def is_enabled(self) -> bool:
        """Check if coverage collection is enabled.

        Returns:
            True if swagger is configured or specs list is non-empty
        """
        return self.swagger is not None or bool(self.specs)
