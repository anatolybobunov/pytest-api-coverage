"""Unit tests for multi_spec loader module."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml
from hypothesis import given
from hypothesis import strategies as st

from pytest_api_coverage.config.multi_spec import (
    load_multi_spec_config,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def two_valid_specs_yaml(tmp_path: Path) -> Path:
    """YAML config file with two valid spec entries."""
    data = {
        "specs": [
            {"name": "users-api", "api_filters": ["http://localhost:8000"], "swagger_path": "users.yaml"},
            {
                "name": "orders-api",
                "api_filters": ["http://localhost:8001"],
                "swagger_url": "http://specs.example.com/orders.yaml",
            },
        ]
    }
    config_file = tmp_path / "coverage-config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")
    return config_file


@pytest.fixture()
def two_valid_specs_json(tmp_path: Path) -> Path:
    """JSON config file with two valid spec entries."""
    data = {
        "specs": [
            {"name": "users-api", "api_filters": ["http://localhost:8000"], "swagger_path": "users.yaml"},
            {
                "name": "orders-api",
                "api_filters": ["http://localhost:8001"],
                "swagger_url": "http://specs.example.com/orders.yaml",
            },
        ]
    }
    config_file = tmp_path / "coverage-config.json"
    config_file.write_text(json.dumps(data), encoding="utf-8")
    return config_file


@pytest.fixture()
def yaml_with_top_level_settings(tmp_path: Path) -> Path:
    """YAML config file with top-level output_dir and formats settings."""
    data = {
        "output_dir": "reports/api",
        "formats": ["json", "html"],
        "specs": [
            {"name": "users-api", "api_filters": ["http://localhost:8000"]},
        ],
    }
    config_file = tmp_path / "coverage-config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")
    return config_file


# ---------------------------------------------------------------------------
# load_multi_spec_config: valid files
# ---------------------------------------------------------------------------


def test_load_yaml_valid(two_valid_specs_yaml: Path) -> None:
    """load_multi_spec_config(yaml_file) returns list of 2 SpecConfig objects."""
    specs, _ = load_multi_spec_config(two_valid_specs_yaml)
    assert len(specs) == 2
    assert specs[0].name == "users-api"
    assert specs[1].name == "orders-api"


def test_load_json_valid(two_valid_specs_json: Path) -> None:
    """load_multi_spec_config(json_file) returns list of 2 SpecConfig objects."""
    specs, _ = load_multi_spec_config(two_valid_specs_json)
    assert len(specs) == 2
    assert specs[0].name == "users-api"
    assert specs[1].name == "orders-api"


def test_load_returns_top_level_settings(yaml_with_top_level_settings: Path) -> None:
    """load_multi_spec_config returns top-level settings in second tuple element."""
    specs, settings = load_multi_spec_config(yaml_with_top_level_settings)
    assert len(specs) == 1
    assert settings["output_dir"] == "reports/api"
    assert settings["formats"] == ["json", "html"]
    assert "specs" not in settings


# ---------------------------------------------------------------------------
# load_multi_spec_config: invalid entries (warn and skip)
# ---------------------------------------------------------------------------


def test_load_skips_missing_name(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Entry without 'name' is skipped; warning logged; others still returned."""
    import logging

    data = {
        "specs": [
            {"api_filters": ["http://localhost:8000"]},  # missing name
            {"name": "orders-api", "api_filters": ["http://localhost:8001"]},
        ]
    }
    config_file = tmp_path / "coverage-config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="pytest_api_coverage"):
        specs, _ = load_multi_spec_config(config_file)

    assert len(specs) == 1
    assert specs[0].name == "orders-api"
    assert "missing" in caplog.text.lower() or "name" in caplog.text.lower()


def test_load_skips_empty_urls(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Entry with api_urls=[] is skipped; warning logged; others still returned."""
    import logging

    data = {
        "specs": [
            {"name": "users-api", "api_filters": []},  # empty api_urls
            {"name": "orders-api", "api_filters": ["http://localhost:8001"]},
        ]
    }
    config_file = tmp_path / "coverage-config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="pytest_api_coverage"):
        specs, _ = load_multi_spec_config(config_file)

    assert len(specs) == 1
    assert specs[0].name == "orders-api"
    assert "url" in caplog.text.lower() or "warn" in caplog.text.lower()


def test_load_skips_both_path_and_url(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Entry with both 'swagger_path' and 'swagger_url' is skipped; warning logged; others still returned."""
    import logging

    data = {
        "specs": [
            {
                "name": "users-api",
                "api_filters": ["http://localhost:8000"],
                "swagger_path": "spec.yaml",
                "swagger_url": "http://example.com/spec.yaml",
            },
            {"name": "orders-api", "api_filters": ["http://localhost:8001"]},
        ]
    }
    config_file = tmp_path / "coverage-config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="pytest_api_coverage"):
        specs, _ = load_multi_spec_config(config_file)

    assert len(specs) == 1
    assert specs[0].name == "orders-api"
    assert "path" in caplog.text.lower() or "url" in caplog.text.lower()


# ---------------------------------------------------------------------------
# load_multi_spec_config: parse failures
# ---------------------------------------------------------------------------


def test_load_invalid_yaml_returns_empty(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """File with invalid YAML returns ([], {}); warning is logged."""
    import logging

    config_file = tmp_path / "coverage-config.yaml"
    config_file.write_text("specs: [\n  - invalid: yaml: content\n  unclosed", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="pytest_api_coverage"):
        specs, settings = load_multi_spec_config(config_file)

    assert specs == []
    assert settings == {}
    assert "warn" in caplog.text.lower() or "failed" in caplog.text.lower() or "error" in caplog.text.lower()


def test_load_empty_specs_list(tmp_path: Path) -> None:
    """File with specs: [] returns ([], {})."""
    data = {"specs": []}
    config_file = tmp_path / "coverage-config.yaml"
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    specs, settings = load_multi_spec_config(config_file)

    assert specs == []
    assert settings == {}


# ---------------------------------------------------------------------------
# api_urls type validation
# ---------------------------------------------------------------------------


class TestApiUrlsTypeValidation:
    def test_api_urls_as_string_is_rejected(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """api_urls as a plain string must be rejected with a warning, spec skipped."""
        import logging

        data = {
            "specs": [
                {
                    "name": "users-api",
                    "swagger_path": "users.yaml",
                    "api_filters": "https://api.example.com",  # string, not list
                }
            ]
        }
        config_file = tmp_path / "coverage-config.yaml"
        config_file.write_text(yaml.dump(data), encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger="pytest_api_coverage"):
            specs, _ = load_multi_spec_config(config_file)

        assert specs == [], "string api_urls must cause the spec to be skipped"
        assert "list" in caplog.text.lower() or "invalid" in caplog.text.lower()

    def test_api_urls_as_list_is_accepted(self, tmp_path: Path) -> None:
        """api_urls as a proper list must be accepted."""
        data = {
            "specs": [
                {
                    "name": "users-api",
                    "swagger_path": "users.yaml",
                    "api_filters": ["https://api.example.com"],
                }
            ]
        }
        config_file = tmp_path / "coverage-config.yaml"
        config_file.write_text(yaml.dump(data), encoding="utf-8")

        specs, _ = load_multi_spec_config(config_file)

        assert len(specs) == 1
        assert specs[0].api_filters == ["https://api.example.com"]


class TestMultiSpecLoaderProperties:
    """Property-based tests for load_multi_spec_config using Hypothesis."""

    @given(st.integers(min_value=0, max_value=5), st.integers(min_value=0, max_value=3))
    def test_valid_specs_count(self, n_valid: int, n_invalid: int) -> None:
        """N valid + M invalid entries → exactly N specs returned."""
        tmpdir = tempfile.mkdtemp()
        try:
            valid_entries = [
                {"name": f"spec-{i}", "api_filters": [f"http://api{i}.example.com"]} for i in range(n_valid)
            ]
            # Entries with empty name are skipped by _parse_spec_entry
            invalid_entries = [
                {"name": "", "api_filters": [f"http://invalid{i}.example.com"]} for i in range(n_invalid)
            ]
            config_data: dict = {"specs": valid_entries + invalid_entries}
            config_file = Path(tmpdir) / "coverage-config.yaml"
            config_file.write_text(yaml.dump(config_data))

            specs, _ = load_multi_spec_config(config_file)

            assert len(specs) == n_valid
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @given(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=20).filter(lambda s: s != "specs"),
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=30),
    )
    def test_top_level_settings_passthrough(self, key: str, value: str) -> None:
        """Arbitrary top-level keys (other than 'specs') are returned unchanged."""
        tmpdir = tempfile.mkdtemp()
        try:
            config_data = {"specs": [], key: value}
            config_file = Path(tmpdir) / "coverage-config.yaml"
            config_file.write_text(yaml.dump(config_data))

            _, top_level = load_multi_spec_config(config_file)

            assert key in top_level
            assert top_level[key] == value
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @given(st.binary(min_size=1))
    def test_parse_failure_safety(self, data: bytes) -> None:
        """Random bytes written to a .yaml file never cause an exception; result is always a tuple."""
        tmpdir = tempfile.mkdtemp()
        try:
            config_file = Path(tmpdir) / "coverage-config.yaml"
            config_file.write_bytes(data)

            specs, settings = load_multi_spec_config(config_file)

            assert isinstance(specs, list)
            assert isinstance(settings, dict)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
