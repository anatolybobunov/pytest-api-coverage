"""Tests for CoverageSettings configuration."""

from pathlib import Path

import pytest

from pytest_api_coverage.config.settings import CoverageSettings


class TestCoverageSettingsInit:
    """Tests for CoverageSettings initialization and validation."""

    def test_default_values(self):
        """Test default settings values."""
        settings = CoverageSettings()

        assert settings.spec is None
        assert settings.output_dir == Path("coverage-output")
        assert settings.formats == {"json", "csv", "html"}
        assert settings.strip_prefixes == []
        assert settings.split_by_origin is False

    def test_spec_file_path_valid(self, tmp_path: Path):
        """Test spec validation with valid file path."""
        spec_file = tmp_path / "swagger.json"
        spec_file.write_text('{"swagger": "2.0"}')

        settings = CoverageSettings(spec=spec_file)

        assert settings.spec == spec_file

    def test_spec_file_path_not_found(self):
        """Test spec validation with non-existent file."""
        with pytest.raises(ValueError, match="Swagger file not found"):
            CoverageSettings(spec="/nonexistent/swagger.json")

    def test_spec_url_passthrough(self):
        """Test that URLs are passed through without validation."""
        url = "https://api.example.com/swagger.json"
        settings = CoverageSettings(spec=url)

        assert settings.spec == url

    def test_spec_http_url_passthrough(self):
        """Test that HTTP URLs are passed through without validation."""
        url = "http://localhost:8080/swagger.json"
        settings = CoverageSettings(spec=url)

        assert settings.spec == url

    def test_formats_from_string(self):
        """Test formats parsing from comma-separated string."""
        settings = CoverageSettings(formats="json, html")

        assert settings.formats == {"json", "html"}

    def test_formats_from_list(self):
        """Test formats from list input."""
        settings = CoverageSettings(formats=["json", "csv"])

        assert settings.formats == {"json", "csv"}

    def test_formats_from_tuple(self):
        """Test formats from tuple input."""
        settings = CoverageSettings(formats=("json",))

        assert settings.formats == {"json"}

    def test_output_dir_from_string(self):
        """Test output_dir conversion from string."""
        settings = CoverageSettings(output_dir="custom-output")

        assert settings.output_dir == Path("custom-output")

    def test_output_dir_from_path(self):
        """Test output_dir from Path input."""
        settings = CoverageSettings(output_dir=Path("my-output"))

        assert settings.output_dir == Path("my-output")

    def test_strip_prefixes_from_string(self):
        """Test strip_prefixes parsing from comma-separated string."""
        settings = CoverageSettings(strip_prefixes="/api/v1, /api/v2")

        assert settings.strip_prefixes == ["/api/v1", "/api/v2"]

    def test_strip_prefixes_from_list(self):
        """Test strip_prefixes from list input."""
        settings = CoverageSettings(strip_prefixes=["/v1", "/v2"])

        assert settings.strip_prefixes == ["/v1", "/v2"]

    def test_strip_prefixes_empty_string(self):
        """Test strip_prefixes with empty string."""
        settings = CoverageSettings(strip_prefixes="")

        assert settings.strip_prefixes == []


class TestCoverageSettingsFromDict:
    """Tests for from_dict deserialization."""

    def test_from_dict_full(self, tmp_path: Path):
        """Test full deserialization from dict."""
        spec_file = tmp_path / "swagger.json"
        spec_file.write_text("{}")

        data = {
            "spec": str(spec_file),
            "output_dir": "output",
            "formats": ["json"],
            "strip_prefixes": ["/v1"],
            "split_by_origin": True,
        }

        settings = CoverageSettings.from_dict(data)

        assert settings.spec == spec_file
        assert settings.output_dir == Path("output")
        assert settings.formats == {"json"}
        assert settings.strip_prefixes == ["/v1"]
        assert settings.split_by_origin is True

    def test_from_dict_url_spec(self):
        """Test from_dict with URL spec (no file validation)."""
        data = {"spec": "https://api.com/swagger.json"}

        settings = CoverageSettings.from_dict(data)

        assert settings.spec == "https://api.com/swagger.json"

    def test_from_dict_defaults(self):
        """Test from_dict with empty dict uses defaults."""
        settings = CoverageSettings.from_dict({})

        assert settings.spec is None
        assert settings.formats == {"json", "csv", "html"}

    def test_from_dict_none_spec(self):
        """Test from_dict with None spec value."""
        data = {"spec": None}

        settings = CoverageSettings.from_dict(data)

        assert settings.spec is None


class TestCoverageSettingsToDict:
    """Tests for to_dict serialization."""

    def test_to_dict_roundtrip(self, tmp_path: Path):
        """Test serialization/deserialization roundtrip."""
        spec_file = tmp_path / "swagger.json"
        spec_file.write_text("{}")

        original = CoverageSettings(
            spec=spec_file,
            formats={"json", "html"},
            split_by_origin=True,
        )

        data = original.to_dict()
        restored = CoverageSettings.from_dict(data)

        assert restored.spec == original.spec
        assert restored.formats == original.formats
        assert restored.split_by_origin == original.split_by_origin

    def test_to_dict_structure(self, tmp_path: Path):
        """Test to_dict returns expected structure."""
        spec_file = tmp_path / "swagger.json"
        spec_file.write_text("{}")

        settings = CoverageSettings(
            spec=spec_file,
            output_dir=Path("output"),
            formats={"json"},
            strip_prefixes=["/v1"],
            split_by_origin=True,
        )

        data = settings.to_dict()

        assert data["spec"] == str(spec_file)
        assert data["output_dir"] == "output"
        assert data["formats"] == ["json"]
        assert data["strip_prefixes"] == ["/v1"]
        assert data["split_by_origin"] is True

    def test_to_dict_none_spec(self):
        """Test to_dict with None spec."""
        settings = CoverageSettings()

        data = settings.to_dict()

        assert data["spec"] is None


class TestCoverageSettingsIsEnabled:
    """Tests for is_enabled method."""

    def test_is_enabled_with_spec_file(self, tmp_path: Path):
        """Test is_enabled returns True when spec file is set."""
        spec_file = tmp_path / "swagger.json"
        spec_file.write_text("{}")

        settings = CoverageSettings(spec=spec_file)

        assert settings.is_enabled() is True

    def test_is_enabled_with_spec_url(self):
        """Test is_enabled returns True when spec URL is set."""
        settings = CoverageSettings(spec="https://api.com/swagger.json")

        assert settings.is_enabled() is True

    def test_is_enabled_without_spec(self):
        """Test is_enabled returns False when spec is None."""
        settings = CoverageSettings()

        assert settings.is_enabled() is False


class TestSpecConfigRoundTrip:
    """Tests for SpecConfig xdist serialisation round-trip (COMPAT-03)."""

    def test_round_trip_with_path(self):
        from pathlib import Path

        from pytest_api_coverage.config.settings import SpecConfig

        original = SpecConfig(
            name="auth", api_urls=["https://auth.example.com"], swagger_path=Path("/tmp/auth.yaml")
        )
        data = original.to_dict()
        # swagger_path must be str in dict (JSON-safe)
        assert isinstance(data["swagger_path"], str)
        restored = SpecConfig.from_dict(data)
        assert restored.name == "auth"
        assert restored.api_urls == ["https://auth.example.com"]
        assert restored.swagger_path == Path("/tmp/auth.yaml")
        assert restored.swagger_url is None

    def test_round_trip_with_url(self):
        from pytest_api_coverage.config.settings import SpecConfig

        original = SpecConfig(
            name="orders",
            api_urls=["https://orders.example.com/api"],
            swagger_url="https://remote.example.com/spec.yaml",
        )
        data = original.to_dict()
        restored = SpecConfig.from_dict(data)
        assert restored.name == "orders"
        assert restored.swagger_url == "https://remote.example.com/spec.yaml"
        assert restored.swagger_path is None

    def test_round_trip_multi_url(self):
        from pytest_api_coverage.config.settings import SpecConfig

        original = SpecConfig(name="svc", api_urls=["https://a.example.com", "https://b.example.com"])
        restored = SpecConfig.from_dict(original.to_dict())
        assert restored.api_urls == ["https://a.example.com", "https://b.example.com"]

    def test_swagger_path_none_round_trips(self):
        from pytest_api_coverage.config.settings import SpecConfig

        original = SpecConfig(name="svc", api_urls=["https://svc.example.com"])
        data = original.to_dict()
        assert data["swagger_path"] is None
        restored = SpecConfig.from_dict(data)
        assert restored.swagger_path is None


class TestCoverageSettingsFromPytestConfig:
    """Tests for from_pytest_config (requires mocker)."""

    def test_from_pytest_config(self, mocker):
        """Test creation from pytest config object."""
        mock_config = mocker.Mock()
        mock_config.getoption.side_effect = lambda key, default=None: {
            "coverage_spec": "https://api.com/swagger.json",
            "coverage_output": "output",
            "coverage_format": "json,html",
            "coverage_strip_prefix": None,
            "coverage_split_by_origin": False,
        }.get(key, default)

        settings = CoverageSettings.from_pytest_config(mock_config)

        assert settings.spec == "https://api.com/swagger.json"
        assert settings.output_dir == Path("output")
        assert settings.formats == {"json", "html"}

    def test_from_pytest_config_defaults(self, mocker):
        """Test from_pytest_config with default values."""
        mock_config = mocker.Mock()
        mock_config.getoption.side_effect = lambda key, default=None: {
            "coverage_spec": None,
            "coverage_output": "coverage-output",
            "coverage_format": "json,csv,html",
            "coverage_strip_prefix": None,
            "coverage_split_by_origin": False,
            "coverage_config": None,
            "coverage_spec_name": None,
            "coverage_spec_api_url": None,
        }.get(key, default)
        # rootpath must be a real Path so _discover_config_file can use / operator
        mock_config.rootpath = Path("/tmp")

        settings = CoverageSettings.from_pytest_config(mock_config)

        assert settings.spec is None
        assert settings.output_dir == Path("coverage-output")
        assert settings.formats == {"json", "csv", "html"}
        assert settings.is_enabled() is False

    def test_from_pytest_config_with_strip_prefix(self, mocker):
        """Test from_pytest_config with strip prefix option."""
        mock_config = mocker.Mock()
        mock_config.getoption.side_effect = lambda key, default=None: {
            "coverage_spec": "https://api.com/spec.json",
            "coverage_output": "coverage-output",
            "coverage_format": "json",
            "coverage_strip_prefix": "/api/v1,/api/v2",
            "coverage_split_by_origin": True,
        }.get(key, default)

        settings = CoverageSettings.from_pytest_config(mock_config)

        assert settings.strip_prefixes == ["/api/v1", "/api/v2"]
        assert settings.split_by_origin is True
