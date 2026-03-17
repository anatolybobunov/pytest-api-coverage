"""Unit tests for extended CoverageSettings — specs field, CLI flag wiring, is_enabled."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pytest_api_coverage.config.settings import CoverageSettings, SpecConfig


def _make_mock_config(mocker: Any, overrides: dict[str, Any] | None = None) -> Any:
    """Create a mock pytest.Config with standard option defaults."""
    defaults: dict[str, Any] = {
        "coverage_spec": None,
        "coverage_output": "api-coverage-report",
        "coverage_format": "html",
        "coverage_strip_prefix": None,
        "coverage_split_by_origin": False,
        "coverage_config": None,
        "coverage_spec_name": None,
        "coverage_spec_api_url": None,
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

    def test_is_enabled_spec(self) -> None:
        """is_enabled() returns True when spec is set."""
        settings = CoverageSettings(spec="https://api.example.com/swagger.json")
        assert settings.is_enabled() is True

    def test_is_enabled_specs_list(self) -> None:
        """is_enabled() returns True when specs list is non-empty."""
        settings = CoverageSettings(
            specs=[SpecConfig(name="auth", api_urls=["https://auth.example.com"], swagger_path="./auth.yaml")]
        )
        assert settings.is_enabled() is True

    def test_is_enabled_false_when_neither(self) -> None:
        """is_enabled() returns False when neither spec nor specs are set."""
        settings = CoverageSettings()
        assert settings.is_enabled() is False


class TestToDict:
    """Tests for CoverageSettings.to_dict() with specs."""

    def test_to_dict_includes_specs(self) -> None:
        """to_dict()['specs'] is a list of dicts, not SpecConfig objects."""
        settings = CoverageSettings(
            specs=[SpecConfig(name="auth", api_urls=["https://auth.example.com"], swagger_path="./auth.yaml")]
        )
        result = settings.to_dict()
        assert "specs" in result
        assert isinstance(result["specs"], list)
        assert len(result["specs"]) == 1
        spec_dict = result["specs"][0]
        assert isinstance(spec_dict, dict)
        assert spec_dict["name"] == "auth"
        assert spec_dict["swagger_path"] == "auth.yaml"  # Path("./auth.yaml") normalises to "auth.yaml"


class TestFromDict:
    """Tests for CoverageSettings.from_dict() with specs."""

    def test_from_dict_reconstructs_specs(self) -> None:
        """from_dict() reconstructs SpecConfig objects from the specs list."""
        settings = CoverageSettings.from_dict(
            {"specs": [{"name": "auth", "api_urls": ["https://auth.example.com"], "swagger_path": "./auth.yaml"}]}
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
        """CLI flags with local path assemble a single SpecConfig with name, swagger_path, and api_urls."""
        mock_config = _make_mock_config(
            mocker,
            {
                "coverage_spec": "./auth.yaml",
                "coverage_spec_name": "auth",
                "coverage_spec_api_url": ["https://auth.example.com"],
            },
        )
        settings = CoverageSettings.from_pytest_config(mock_config)
        assert len(settings.specs) == 1
        spec = settings.specs[0]
        assert spec.name == "auth"
        assert spec.swagger_path == Path("auth.yaml")  # Path("./auth.yaml") normalises to Path("auth.yaml")
        assert spec.api_urls == ["https://auth.example.com"]

    def test_from_pytest_config_cli_spec_url(self, mocker: Any) -> None:
        """CLI flags with URL assemble a single SpecConfig with swagger_url set."""
        mock_config = _make_mock_config(
            mocker,
            {
                "coverage_spec": "https://orders.example.com/openapi.json",
                "coverage_spec_name": "orders",
                "coverage_spec_api_url": ["https://orders.example.com"],
            },
        )
        settings = CoverageSettings.from_pytest_config(mock_config)
        assert len(settings.specs) == 1
        spec = settings.specs[0]
        assert spec.name == "orders"
        assert spec.swagger_url == "https://orders.example.com/openapi.json"
        assert spec.api_urls == ["https://orders.example.com"]

    def test_from_pytest_config_no_spec_flags_no_specs(self, mocker: Any) -> None:
        """When all spec options are None, specs is empty."""
        mock_config = _make_mock_config(mocker)
        settings = CoverageSettings.from_pytest_config(mock_config)
        assert settings.specs == []

    def test_from_pytest_config_api_url_none_defers_error(self, mocker: Any) -> None:
        """coverage_spec_api_url=None with a spec name must defer the error, not exit immediately."""
        mock_config = _make_mock_config(
            mocker,
            {
                "coverage_spec": "./auth.yaml",
                "coverage_spec_name": "auth",
                "coverage_spec_api_url": None,
            },
        )
        settings = CoverageSettings.from_pytest_config(mock_config)
        assert settings.config_error is not None
        assert "--coverage-spec-api-url" in settings.config_error


def test_spec_name_without_spec_defers_error(tmp_path, mocker):
    """Missing --coverage-spec with --coverage-spec-name must defer the error, not exit immediately."""
    from unittest.mock import MagicMock

    config = MagicMock()
    config.getoption.side_effect = lambda key, default=None: {
        "coverage_spec": None,
        "coverage_spec_name": "auth",
        "coverage_spec_api_url": None,
        "coverage_config": None,
        "coverage_output": "api-coverage-report",
        "coverage_format": "html",
        "coverage_strip_prefix": None,
        "coverage_split_by_origin": False,
    }.get(key, default)
    config.rootpath = tmp_path  # tmp_path has no config file to discover

    settings = CoverageSettings.from_pytest_config(config)
    assert settings.config_error is not None
    assert "--coverage-spec" in settings.config_error


def test_spec_name_filters_config_specs(tmp_path, mocker):
    """--coverage-spec-name with coverage_config filters specs, but requires --coverage-spec for CLI mode."""
    from unittest.mock import MagicMock

    spec_file_auth = tmp_path / "auth.yaml"
    spec_file_auth.write_text("openapi: '3.0.0'")
    spec_file_orders = tmp_path / "orders.yaml"
    spec_file_orders.write_text("openapi: '3.0.0'")

    config_file = tmp_path / "coverage-config.yaml"
    config_file.write_text(
        f"specs:\n"
        f"  - name: auth\n"
        f"    api_urls:\n"
        f"      - https://auth.example.com\n"
        f"    swagger_path: {spec_file_auth}\n"
        f"  - name: orders\n"
        f"    api_urls:\n"
        f"      - https://orders.example.com\n"
        f"    swagger_path: {spec_file_orders}\n"
    )

    config = MagicMock()
    config.getoption.side_effect = lambda key, default=None: {
        "coverage_spec": None,
        "coverage_spec_name": "auth",
        "coverage_spec_api_url": None,
        "coverage_config": str(config_file),
        "coverage_output": "api-coverage-report",
        "coverage_format": "html",
        "coverage_strip_prefix": None,
        "coverage_split_by_origin": False,
    }.get(key, default)
    config.rootpath = tmp_path

    settings = CoverageSettings.from_pytest_config(config)
    assert settings.config_error is not None
    assert "--coverage-spec" in settings.config_error


class TestDeferredUsageError:
    def test_from_pytest_config_stores_error_instead_of_raising(self, mocker: Any) -> None:
        """from_pytest_config must store errors in config_error, not raise."""
        mock_config = _make_mock_config(
            mocker,
            {
                "coverage_spec": "./auth.yaml",
                "coverage_spec_name": "auth",
                "coverage_spec_api_url": None,
            },
        )
        # Must NOT raise
        settings = CoverageSettings.from_pytest_config(mock_config)
        assert settings.config_error is not None
        assert "--coverage-spec-api-url" in settings.config_error

    def test_raise_if_error_raises_usage_error(self) -> None:
        """raise_if_error() must raise pytest.UsageError with stored message."""
        import pytest

        settings = CoverageSettings(config_error="[api-coverage] some config error")
        with pytest.raises(pytest.UsageError, match="some config error"):
            settings.raise_if_error()

    def test_raise_if_error_is_noop_when_no_error(self) -> None:
        """raise_if_error() must be a no-op when config_error is None."""
        settings = CoverageSettings()
        settings.raise_if_error()  # must not raise

    def test_is_enabled_when_config_error_set(self) -> None:
        """is_enabled() must return True when config_error is set."""
        settings = CoverageSettings(config_error="[api-coverage] some error")
        assert settings.is_enabled() is True


def test_spec_name_no_match_defers_error(tmp_path, mocker):
    """--coverage-spec-name without --coverage-spec defers an error regardless of config file."""
    from unittest.mock import MagicMock

    spec_file = tmp_path / "auth.yaml"
    spec_file.write_text("openapi: '3.0.0'")
    config_file = tmp_path / "coverage-config.yaml"
    config_file.write_text(
        f"specs:\n"
        f"  - name: auth\n"
        f"    api_urls:\n"
        f"      - https://auth.example.com\n"
        f"    swagger_path: {spec_file}\n"
    )

    config = MagicMock()
    config.getoption.side_effect = lambda key, default=None: {
        "coverage_spec": None,
        "coverage_spec_name": "nonexistent",
        "coverage_spec_api_url": None,
        "coverage_config": str(config_file),
        "coverage_output": "api-coverage-report",
        "coverage_format": "html",
        "coverage_strip_prefix": None,
        "coverage_split_by_origin": False,
    }.get(key, default)
    config.rootpath = tmp_path

    settings = CoverageSettings.from_pytest_config(config)
    assert settings.config_error is not None
    assert "--coverage-spec" in settings.config_error


def test_spec_name_autodiscover_defers_error_without_coverage_spec(tmp_path, mocker):
    """Auto-discovered config + --coverage-spec-name without --coverage-spec defers an error."""
    from unittest.mock import MagicMock

    spec_file_a = tmp_path / "a.yaml"
    spec_file_a.write_text("openapi: '3.0.0'")
    spec_file_b = tmp_path / "b.yaml"
    spec_file_b.write_text("openapi: '3.0.0'")

    # Place the config file where auto-discovery will find it
    config_file = tmp_path / "coverage-config.yaml"
    config_file.write_text(
        f"specs:\n"
        f"  - name: svc-a\n"
        f"    api_urls:\n"
        f"      - https://a.example.com\n"
        f"    swagger_path: {spec_file_a}\n"
        f"  - name: svc-b\n"
        f"    api_urls:\n"
        f"      - https://b.example.com\n"
        f"    swagger_path: {spec_file_b}\n"
    )

    config = MagicMock()
    config.getoption.side_effect = lambda key, default=None: {
        "coverage_spec": None,
        "coverage_spec_name": "svc-b",
        "coverage_spec_api_url": None,
        "coverage_config": None,  # no explicit config — use autodiscovery
        "coverage_output": "api-coverage-report",
        "coverage_format": "html",
        "coverage_strip_prefix": None,
        "coverage_split_by_origin": False,
    }.get(key, default)
    config.rootpath = tmp_path

    settings = CoverageSettings.from_pytest_config(config)
    assert settings.config_error is not None
    assert "--coverage-spec" in settings.config_error


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
        f"    api_urls:\n"
        f"      - https://api.example.com\n"
        f"    swagger_path: {spec_file}\n"
    )

    config = MagicMock()
    config.getoption.side_effect = lambda key, default=None: {
        "coverage_spec": None,
        "coverage_spec_name": None,
        "coverage_spec_api_url": None,
        "coverage_config": str(config_file),
        "coverage_output": "api-coverage-report",  # default value
        "coverage_format": "html",
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
        "coverage_spec": None,
        "coverage_spec_name": None,
        "coverage_spec_api_url": None,
        "coverage_config": str(config_file),
        "coverage_output": "from-cli",  # explicit CLI value
        "coverage_format": "html",
        "coverage_strip_prefix": None,
        "coverage_split_by_origin": False,
    }.get(key, default)
    config.rootpath = tmp_path

    settings = CoverageSettings.from_pytest_config(config)
    assert settings.output_dir == Path("from-cli")
