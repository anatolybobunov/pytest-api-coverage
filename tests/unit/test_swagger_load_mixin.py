"""Unit tests for _SwaggerLoadMixin — verifies exc_info is preserved on load failure."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pytest_api_coverage.config.settings import CoverageSettings
from pytest_api_coverage.plugin import _SwaggerLoadMixin
from pytest_api_coverage.schemas import SwaggerSpec


class _ConcreteSwaggerLoader(_SwaggerLoadMixin):
    """Minimal concrete subclass of _SwaggerLoadMixin for isolated testing."""

    def __init__(self, settings: CoverageSettings) -> None:
        self.settings = settings
        self.swagger_spec: SwaggerSpec | None = None
        self._swagger_load_error: str | None = None


class TestSwaggerLoadMixinExcInfo:
    def test_failed_swagger_load_includes_traceback_in_log(self, tmp_path: Path, caplog) -> None:
        """When swagger fails to load, exc_info must be present in the log record."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text(": invalid: yaml [unclosed", encoding="utf-8")

        settings = CoverageSettings(spec=bad_yaml)
        loader = _ConcreteSwaggerLoader(settings)

        with caplog.at_level(logging.WARNING, logger="pytest_api_coverage"):
            loader._load_swagger()

        assert any(r.exc_info is not None for r in caplog.records), (
            "Expected exc_info in log record — add exc_info=True to logger.warning in _SwaggerLoadMixin._load_swagger"
        )

    def test_failed_swagger_load_sets_error_string(self, tmp_path: Path) -> None:
        """_swagger_load_error is populated with a string description on failure."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text(": invalid: yaml [unclosed", encoding="utf-8")

        settings = CoverageSettings(spec=bad_yaml)
        loader = _ConcreteSwaggerLoader(settings)
        loader._load_swagger()

        assert loader._swagger_load_error is not None
        assert isinstance(loader._swagger_load_error, str)
        assert len(loader._swagger_load_error) > 0

    def test_no_spec_configured_is_noop(self) -> None:
        """_load_swagger() is a no-op when settings.spec is None."""
        settings = CoverageSettings()
        loader = _ConcreteSwaggerLoader(settings)
        loader._load_swagger()

        assert loader.swagger_spec is None
        assert loader._swagger_load_error is None
