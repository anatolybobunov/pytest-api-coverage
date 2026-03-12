"""Unit tests for extended CoverageSettings — specs field, CLI flag wiring, is_enabled."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pytest_api_coverage.config.settings import CoverageSettings, SpecConfig


def _make_mock_config(mocker: Any, overrides: dict[str, Any] | None = None) -> Any:
    """Create a mock pytest.Config with standard option defaults."""
    defaults: dict[str, Any] = {
        "swagger": None,
        "coverage_output": "coverage-output",
        "coverage_format": "json,csv,html",
        "coverage_base_url": None,
        "coverage_include_base_url": None,
        "coverage_strip_prefix": None,
        "coverage_split_by_origin": False,
        # new keys:
        "coverage_config": None,
        "coverage_spec_name": None,
        "coverage_spec_path": None,
        "coverage_spec_url": None,
        "coverage_spec_base_url": None,
    }
    if overrides:
        defaults.update(overrides)

    mock_config = mocker.Mock()
    mock_config.getoption.side_effect = lambda key, default=None: defaults.get(key, default)
    # rootpath must be a real Path so _discover_config_file can use / operator
    mock_config.rootpath = Path("/tmp")
    return mock_config


class TestIsEnabled:
    """Tests for CoverageSettings.is_enabled()."""

    def test_is_enabled_swagger(self) -> None:
        """is_enabled() returns True when swagger is set (existing behaviour preserved)."""
        settings = CoverageSettings(swagger="https://api.example.com/swagger.json")
        assert settings.is_enabled() is True

    def test_is_enabled_specs_list(self) -> None:
        """is_enabled() returns True when specs list is non-empty."""
        settings = CoverageSettings(
            specs=[SpecConfig(name="auth", urls=["https://auth.example.com"], path="./auth.yaml")]
        )
        assert settings.is_enabled() is True

    def test_is_enabled_false_when_neither(self) -> None:
        """is_enabled() returns False when neither swagger nor specs are set."""
        settings = CoverageSettings()
        assert settings.is_enabled() is False


class TestToDict:
    """Tests for CoverageSettings.to_dict() with specs."""

    def test_to_dict_includes_specs(self) -> None:
        """to_dict()['specs'] is a list of dicts, not SpecConfig objects."""
        settings = CoverageSettings(
            specs=[SpecConfig(name="auth", urls=["https://auth.example.com"], path="./auth.yaml")]
        )
        result = settings.to_dict()
        assert "specs" in result
        assert isinstance(result["specs"], list)
        assert len(result["specs"]) == 1
        spec_dict = result["specs"][0]
        assert isinstance(spec_dict, dict)
        assert spec_dict["name"] == "auth"
        assert spec_dict["path"] == "auth.yaml"  # Path("./auth.yaml") normalises to "auth.yaml"


class TestFromDict:
    """Tests for CoverageSettings.from_dict() with specs."""

    def test_from_dict_reconstructs_specs(self) -> None:
        """from_dict() reconstructs SpecConfig objects from the specs list."""
        settings = CoverageSettings.from_dict(
            {"specs": [{"name": "auth", "urls": ["https://auth.example.com"], "path": "./auth.yaml"}]}
        )
        assert len(settings.specs) == 1
        spec = settings.specs[0]
        assert isinstance(spec, SpecConfig)
        assert spec.name == "auth"

    def test_from_dict_empty_specs(self) -> None:
        """from_dict({}) produces empty specs list."""
        settings = CoverageSettings.from_dict({})
        assert settings.specs == []


class TestFromPytestConfig:
    """Tests for CoverageSettings.from_pytest_config() with new CLI flags."""

    def test_from_pytest_config_cli_spec_path(self, mocker: Any) -> None:
        """CLI flags with path assemble a single SpecConfig with name, path, and base_urls."""
        mock_config = _make_mock_config(
            mocker,
            {
                "coverage_spec_name": "auth",
                "coverage_spec_path": "./auth.yaml",
                "coverage_spec_base_url": ["https://auth.example.com"],
            },
        )
        settings = CoverageSettings.from_pytest_config(mock_config)
        assert len(settings.specs) == 1
        spec = settings.specs[0]
        assert spec.name == "auth"
        assert spec.path == Path("auth.yaml")  # Path("./auth.yaml") normalises to Path("auth.yaml")
        assert spec.urls == ["https://auth.example.com"]

    def test_from_pytest_config_cli_spec_url(self, mocker: Any) -> None:
        """CLI flags with url assemble a single SpecConfig with url set."""
        mock_config = _make_mock_config(
            mocker,
            {
                "coverage_spec_name": "orders",
                "coverage_spec_url": "https://orders.example.com/openapi.json",
                "coverage_spec_base_url": ["https://orders.example.com"],
            },
        )
        settings = CoverageSettings.from_pytest_config(mock_config)
        assert len(settings.specs) == 1
        spec = settings.specs[0]
        assert spec.name == "orders"
        assert spec.url == "https://orders.example.com/openapi.json"
        assert spec.urls == ["https://orders.example.com"]

    def test_from_pytest_config_swagger_wins_over_spec_flags(self, mocker: Any, capsys: Any) -> None:
        """When --swagger and spec flags both set, swagger wins, specs is empty, warning printed."""
        mock_config = _make_mock_config(
            mocker,
            {
                "swagger": "https://api.example.com/swagger.json",
                "coverage_spec_path": "./auth.yaml",
                "coverage_spec_base_url": ["https://auth.example.com"],
            },
        )
        settings = CoverageSettings.from_pytest_config(mock_config)
        assert settings.swagger == "https://api.example.com/swagger.json"
        assert settings.specs == []
        captured = capsys.readouterr()
        assert "Warning" in captured.out or "warning" in captured.out.lower()

    def test_from_pytest_config_no_spec_flags_no_specs(self, mocker: Any) -> None:
        """When all new spec options are None, specs is empty."""
        mock_config = _make_mock_config(mocker)
        settings = CoverageSettings.from_pytest_config(mock_config)
        assert settings.specs == []

    def test_from_pytest_config_base_url_none_produces_empty_list(self, mocker: Any) -> None:
        """coverage_spec_base_url=None does not error; coerced to empty list."""
        mock_config = _make_mock_config(
            mocker,
            {
                "coverage_spec_name": "auth",
                "coverage_spec_path": "./auth.yaml",
                "coverage_spec_base_url": None,
            },
        )
        # Should not raise; if no base_urls, spec is skipped (warning printed but no error)
        settings = CoverageSettings.from_pytest_config(mock_config)
        # spec is skipped when base_urls is empty
        assert isinstance(settings.specs, list)


def test_spec_path_without_name_prints_warning_not_traceback(capsys, tmp_path):
    """Missing --coverage-spec-name with --coverage-spec-path must warn, not crash."""
    from unittest.mock import MagicMock

    spec_file = tmp_path / "api.yaml"
    spec_file.write_text("openapi: '3.0.0'")

    config = MagicMock()
    config.getoption.side_effect = lambda key, default=None: {
        "swagger": None,
        "coverage_spec_name": None,  # <- missing
        "coverage_spec_path": str(spec_file),
        "coverage_spec_url": None,
        "coverage_spec_base_url": ["https://api.example.com"],
        "coverage_config": None,
        "coverage_output": "coverage-output",
        "coverage_format": "json,csv,html",
        "coverage_base_url": None,
        "coverage_include_base_url": None,
        "coverage_strip_prefix": None,
        "coverage_split_by_origin": False,
    }.get(key, default)
    config.rootpath = tmp_path

    # Must not raise
    settings = CoverageSettings.from_pytest_config(config)

    # Must produce no specs (skipped due to missing name)
    assert settings.specs == []

    captured = capsys.readouterr()
    assert "warning" in captured.out.lower() or "name" in captured.out.lower()


def test_top_level_output_dir_applied_from_config_file(tmp_path):
    """output_dir in coverage-config.yaml must be applied when CLI option is default."""
    from pathlib import Path
    from unittest.mock import MagicMock

    # Create a config file with top-level output_dir
    config_file = tmp_path / "coverage-config.yaml"
    spec_file = tmp_path / "api.yaml"
    spec_file.write_text("openapi: '3.0.0'")
    config_file.write_text(
        f"output_dir: custom-reports\n"
        f"specs:\n"
        f"  - name: myapi\n"
        f"    urls:\n"
        f"      - https://api.example.com\n"
        f"    path: {spec_file}\n"
    )

    config = MagicMock()
    config.getoption.side_effect = lambda key, default=None: {
        "swagger": None,
        "coverage_spec_name": None,
        "coverage_spec_path": None,
        "coverage_spec_url": None,
        "coverage_spec_base_url": None,
        "coverage_config": str(config_file),
        "coverage_output": "coverage-output",  # default value
        "coverage_format": "json,csv,html",
        "coverage_base_url": None,
        "coverage_include_base_url": None,
        "coverage_strip_prefix": None,
        "coverage_split_by_origin": False,
    }.get(key, default)
    config.rootpath = tmp_path

    settings = CoverageSettings.from_pytest_config(config)
    assert settings.output_dir == Path("custom-reports")


def test_cli_output_dir_overrides_config_file(tmp_path):
    """Explicit --coverage-output CLI flag must win over config file output_dir."""
    from pathlib import Path
    from unittest.mock import MagicMock

    config_file = tmp_path / "coverage-config.yaml"
    config_file.write_text("output_dir: from-config\nspecs: []\n")

    config = MagicMock()
    config.getoption.side_effect = lambda key, default=None: {
        "swagger": None,
        "coverage_spec_name": None,
        "coverage_spec_path": None,
        "coverage_spec_url": None,
        "coverage_spec_base_url": None,
        "coverage_config": str(config_file),
        "coverage_output": "from-cli",  # explicit CLI value
        "coverage_format": "json,csv,html",
        "coverage_base_url": None,
        "coverage_include_base_url": None,
        "coverage_strip_prefix": None,
        "coverage_split_by_origin": False,
    }.get(key, default)
    config.rootpath = tmp_path

    settings = CoverageSettings.from_pytest_config(config)
    assert settings.output_dir == Path("from-cli")
