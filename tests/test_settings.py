"""Tests for CoverageSettings configuration."""

from pathlib import Path

import pytest

from pytest_api_coverage.config.settings import CoverageSettings


class TestCoverageSettingsInit:
    """Tests for CoverageSettings initialization and validation."""

    def test_default_values(self):
        """Test default settings values."""
        settings = CoverageSettings()

        assert settings.swagger is None
        assert settings.output_dir == Path("coverage-output")
        assert settings.formats == {"json", "csv", "html"}
        assert settings.base_url is None
        assert settings.include_base_urls == set()
        assert settings.strip_prefixes == []
        assert settings.split_by_origin is False

    def test_swagger_file_path_valid(self, tmp_path: Path):
        """Test swagger validation with valid file path."""
        swagger_file = tmp_path / "swagger.json"
        swagger_file.write_text('{"swagger": "2.0"}')

        settings = CoverageSettings(swagger=swagger_file)

        assert settings.swagger == swagger_file

    def test_swagger_file_path_not_found(self):
        """Test swagger validation with non-existent file."""
        with pytest.raises(ValueError, match="Swagger file not found"):
            CoverageSettings(swagger="/nonexistent/swagger.json")

    def test_swagger_url_passthrough(self):
        """Test that URLs are passed through without validation."""
        url = "https://api.example.com/swagger.json"
        settings = CoverageSettings(swagger=url)

        assert settings.swagger == url

    def test_swagger_http_url_passthrough(self):
        """Test that HTTP URLs are passed through without validation."""
        url = "http://localhost:8080/swagger.json"
        settings = CoverageSettings(swagger=url)

        assert settings.swagger == url

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

    def test_include_base_urls_from_string(self):
        """Test include_base_urls parsing from comma-separated string."""
        settings = CoverageSettings(include_base_urls="https://api.com, https://staging.com")

        assert settings.include_base_urls == {"https://api.com", "https://staging.com"}

    def test_include_base_urls_from_list(self):
        """Test include_base_urls from list input."""
        settings = CoverageSettings(include_base_urls=["https://api.com", "https://staging.com"])

        assert settings.include_base_urls == {"https://api.com", "https://staging.com"}

    def test_include_base_urls_empty_string(self):
        """Test include_base_urls with empty string."""
        settings = CoverageSettings(include_base_urls="")

        assert settings.include_base_urls == set()

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
        swagger_file = tmp_path / "swagger.json"
        swagger_file.write_text("{}")

        data = {
            "swagger": str(swagger_file),
            "output_dir": "output",
            "formats": ["json"],
            "base_url": "https://api.com",
            "include_base_urls": ["https://a.com", "https://b.com"],
            "strip_prefixes": ["/v1"],
            "split_by_origin": True,
        }

        settings = CoverageSettings.from_dict(data)

        assert settings.swagger == swagger_file
        assert settings.output_dir == Path("output")
        assert settings.formats == {"json"}
        assert settings.base_url == "https://api.com"
        assert settings.include_base_urls == {"https://a.com", "https://b.com"}
        assert settings.strip_prefixes == ["/v1"]
        assert settings.split_by_origin is True

    def test_from_dict_url_swagger(self):
        """Test from_dict with URL swagger (no file validation)."""
        data = {"swagger": "https://api.com/swagger.json"}

        settings = CoverageSettings.from_dict(data)

        assert settings.swagger == "https://api.com/swagger.json"

    def test_from_dict_defaults(self):
        """Test from_dict with empty dict uses defaults."""
        settings = CoverageSettings.from_dict({})

        assert settings.swagger is None
        assert settings.formats == {"json", "csv", "html"}

    def test_from_dict_none_swagger(self):
        """Test from_dict with None swagger value."""
        data = {"swagger": None}

        settings = CoverageSettings.from_dict(data)

        assert settings.swagger is None


class TestCoverageSettingsToDict:
    """Tests for to_dict serialization."""

    def test_to_dict_roundtrip(self, tmp_path: Path):
        """Test serialization/deserialization roundtrip."""
        swagger_file = tmp_path / "swagger.json"
        swagger_file.write_text("{}")

        original = CoverageSettings(
            swagger=swagger_file,
            formats={"json", "html"},
            base_url="https://api.com",
            split_by_origin=True,
        )

        data = original.to_dict()
        restored = CoverageSettings.from_dict(data)

        assert restored.swagger == original.swagger
        assert restored.formats == original.formats
        assert restored.base_url == original.base_url
        assert restored.split_by_origin == original.split_by_origin

    def test_to_dict_structure(self, tmp_path: Path):
        """Test to_dict returns expected structure."""
        swagger_file = tmp_path / "swagger.json"
        swagger_file.write_text("{}")

        settings = CoverageSettings(
            swagger=swagger_file,
            output_dir=Path("output"),
            formats={"json"},
            base_url="https://api.com",
            include_base_urls={"https://a.com"},
            strip_prefixes=["/v1"],
            split_by_origin=True,
        )

        data = settings.to_dict()

        assert data["swagger"] == str(swagger_file)
        assert data["output_dir"] == "output"
        assert data["formats"] == ["json"]
        assert data["base_url"] == "https://api.com"
        assert data["include_base_urls"] == ["https://a.com"]
        assert data["strip_prefixes"] == ["/v1"]
        assert data["split_by_origin"] is True

    def test_to_dict_none_swagger(self):
        """Test to_dict with None swagger."""
        settings = CoverageSettings()

        data = settings.to_dict()

        assert data["swagger"] is None


class TestCoverageSettingsIsEnabled:
    """Tests for is_enabled method."""

    def test_is_enabled_with_swagger_file(self, tmp_path: Path):
        """Test is_enabled returns True when swagger file is set."""
        swagger_file = tmp_path / "swagger.json"
        swagger_file.write_text("{}")

        settings = CoverageSettings(swagger=swagger_file)

        assert settings.is_enabled() is True

    def test_is_enabled_with_swagger_url(self):
        """Test is_enabled returns True when swagger URL is set."""
        settings = CoverageSettings(swagger="https://api.com/swagger.json")

        assert settings.is_enabled() is True

    def test_is_enabled_without_swagger(self):
        """Test is_enabled returns False when swagger is None."""
        settings = CoverageSettings()

        assert settings.is_enabled() is False


class TestCoverageSettingsFromPytestConfig:
    """Tests for from_pytest_config (requires mocker)."""

    def test_from_pytest_config(self, mocker):
        """Test creation from pytest config object."""
        mock_config = mocker.Mock()
        mock_config.getoption.side_effect = lambda key, default=None: {
            "swagger": "https://api.com/swagger.json",
            "coverage_output": "output",
            "coverage_format": "json,html",
            "coverage_base_url": "https://api.com",
            "coverage_include_base_url": None,
            "coverage_strip_prefix": None,
            "coverage_split_by_origin": False,
        }.get(key, default)

        settings = CoverageSettings.from_pytest_config(mock_config)

        assert settings.swagger == "https://api.com/swagger.json"
        assert settings.output_dir == Path("output")
        assert settings.formats == {"json", "html"}
        assert settings.base_url == "https://api.com"

    def test_from_pytest_config_defaults(self, mocker):
        """Test from_pytest_config with default values."""
        mock_config = mocker.Mock()
        mock_config.getoption.side_effect = lambda key, default=None: {
            "swagger": None,
            "coverage_output": "coverage-output",
            "coverage_format": "json,csv,html",
            "coverage_base_url": None,
            "coverage_include_base_url": None,
            "coverage_strip_prefix": None,
            "coverage_split_by_origin": False,
            "coverage_config": None,
            "coverage_spec_name": None,
            "coverage_spec_path": None,
            "coverage_spec_url": None,
            "coverage_spec_base_url": None,
        }.get(key, default)
        # rootpath must be a real Path so _discover_config_file can use / operator
        mock_config.rootpath = Path("/tmp")

        settings = CoverageSettings.from_pytest_config(mock_config)

        assert settings.swagger is None
        assert settings.output_dir == Path("coverage-output")
        assert settings.formats == {"json", "csv", "html"}
        assert settings.is_enabled() is False

    def test_from_pytest_config_with_filters(self, mocker):
        """Test from_pytest_config with filtering options."""
        mock_config = mocker.Mock()
        mock_config.getoption.side_effect = lambda key, default=None: {
            "swagger": "https://api.com/spec.json",
            "coverage_output": "coverage-output",
            "coverage_format": "json",
            "coverage_base_url": "https://api.com",
            "coverage_include_base_url": "https://a.com,https://b.com",
            "coverage_strip_prefix": "/api/v1,/api/v2",
            "coverage_split_by_origin": True,
        }.get(key, default)

        settings = CoverageSettings.from_pytest_config(mock_config)

        assert settings.base_url == "https://api.com"
        assert settings.include_base_urls == {"https://a.com", "https://b.com"}
        assert settings.strip_prefixes == ["/api/v1", "/api/v2"]
        assert settings.split_by_origin is True
