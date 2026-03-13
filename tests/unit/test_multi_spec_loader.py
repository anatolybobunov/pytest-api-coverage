"""Unit tests for multi_spec loader module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from pytest_api_coverage.config.multi_spec import (
    _discover_config_file,
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
            {"name": "users-api", "api_urls": ["http://localhost:8000"], "swagger_path": "users.yaml"},
            {
                "name": "orders-api",
                "api_urls": ["http://localhost:8001"],
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
            {"name": "users-api", "api_urls": ["http://localhost:8000"], "swagger_path": "users.yaml"},
            {
                "name": "orders-api",
                "api_urls": ["http://localhost:8001"],
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
            {"name": "users-api", "api_urls": ["http://localhost:8000"]},
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
            {"api_urls": ["http://localhost:8000"]},  # missing name
            {"name": "orders-api", "api_urls": ["http://localhost:8001"]},
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
            {"name": "users-api", "api_urls": []},  # empty api_urls
            {"name": "orders-api", "api_urls": ["http://localhost:8001"]},
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
                "api_urls": ["http://localhost:8000"],
                "swagger_path": "spec.yaml",
                "swagger_url": "http://example.com/spec.yaml",
            },
            {"name": "orders-api", "api_urls": ["http://localhost:8001"]},
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
# _discover_config_file
# ---------------------------------------------------------------------------


def test_discover_yaml_only(tmp_path: Path) -> None:
    """_discover_config_file returns YAML path when only coverage-config.yaml exists."""
    yaml_file = tmp_path / "coverage-config.yaml"
    yaml_file.write_text("specs: []", encoding="utf-8")

    result = _discover_config_file(tmp_path)

    assert result == yaml_file


def test_discover_json_only(tmp_path: Path) -> None:
    """_discover_config_file returns JSON path when only coverage-config.json exists."""
    json_file = tmp_path / "coverage-config.json"
    json_file.write_text('{"specs": []}', encoding="utf-8")

    result = _discover_config_file(tmp_path)

    assert result == json_file


def test_discover_both_returns_yaml_with_warning(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """_discover_config_file returns YAML path when both exist; warning logged."""
    import logging

    yaml_file = tmp_path / "coverage-config.yaml"
    yaml_file.write_text("specs: []", encoding="utf-8")
    json_file = tmp_path / "coverage-config.json"
    json_file.write_text('{"specs": []}', encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="pytest_api_coverage"):
        result = _discover_config_file(tmp_path)

    assert result == yaml_file
    assert "warn" in caplog.text.lower() or "yaml" in caplog.text.lower()


def test_discover_neither_returns_none(tmp_path: Path) -> None:
    """_discover_config_file returns None when neither file exists."""
    result = _discover_config_file(tmp_path)

    assert result is None
