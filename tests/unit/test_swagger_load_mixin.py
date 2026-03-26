"""Unit tests for _SwaggerLoadMixin — verifies exc_info is preserved on load failure."""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

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
    def test_failed_swagger_load_traceback_at_debug_not_warning(self, tmp_path: Path, caplog) -> None:
        """When swagger fails to load, traceback goes to DEBUG (not WARNING)."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text(": invalid: yaml [unclosed", encoding="utf-8")

        settings = CoverageSettings(spec=bad_yaml)
        loader = _ConcreteSwaggerLoader(settings)

        with caplog.at_level(logging.DEBUG, logger="pytest_api_coverage"):
            loader._load_swagger()

        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]

        # WARNING should be clean (no traceback)
        assert all(r.exc_info is None for r in warning_records), (
            "WARNING log should not include traceback — keep exc_info on DEBUG only"
        )
        # Traceback should appear at DEBUG level
        assert any(r.exc_info is not None for r in debug_records), (
            "Expected exc_info in DEBUG log record — add exc_info=True to logger.debug in _SwaggerLoadMixin._load_swagger"
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


class TestSwaggerLoadMixinProperties:
    """Property-based tests for _SwaggerLoadMixin using Hypothesis."""

    @given(st.binary(min_size=1))
    def test_bad_content_always_sets_error(self, data: bytes) -> None:
        """Random bytes written to a spec file cause _load_swagger to set _swagger_load_error."""
        tmpdir = tempfile.mkdtemp()
        try:
            spec_file = Path(tmpdir) / "spec.yaml"
            spec_file.write_bytes(data)
            settings = CoverageSettings(spec=spec_file)
            loader = _ConcreteSwaggerLoader(settings)
            loader._load_swagger()

            assert loader._swagger_load_error is not None
            assert loader.swagger_spec is None
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
