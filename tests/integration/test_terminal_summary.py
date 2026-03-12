"""Integration tests for terminal summary output and backward compatibility.

Tests requirements:
- OUT-02: Per-spec terminal summary row (name, endpoints, %, req, filename)
- OUT-03: TOTAL row with aggregate coverage and unmatched count
- COMPAT-01: --swagger backward compat (coverage.json/html/csv, no prefix)
- COMPAT-02: xdist multi-spec produces prefixed files
"""

from __future__ import annotations

import pytest

MINIMAL_SPEC = """
openapi: "3.0.0"
info:
  title: Test
  version: "1.0"
paths:
  /users:
    get:
      responses:
        "200":
          description: ok
"""

AUTH_SPEC = """
openapi: "3.0.0"
info:
  title: Auth API
  version: "1.0"
paths:
  /login:
    post:
      responses:
        "200":
          description: ok
"""

ORDERS_SPEC = """
openapi: "3.0.0"
info:
  title: Orders API
  version: "1.0"
paths:
  /orders:
    get:
      responses:
        "200":
          description: ok
"""


def _write_two_spec_config(pytester: pytest.Pytester) -> None:
    """Write auth+orders spec files and coverage-config.yaml."""
    (pytester.path / "auth.yaml").write_text(AUTH_SPEC)
    (pytester.path / "orders.yaml").write_text(ORDERS_SPEC)
    (pytester.path / "coverage-config.yaml").write_text(
        "specs:\n"
        "  - name: auth\n"
        "    path: auth.yaml\n"
        "    urls:\n"
        "      - https://auth.example.com\n"
        "  - name: orders\n"
        "    path: orders.yaml\n"
        "    urls:\n"
        "      - https://orders.example.com\n"
    )


def test_multi_spec_terminal_output(pytester: pytest.Pytester) -> None:
    """Two-spec run: terminal shows one row per spec with endpoints/pct/req/filename."""
    _write_two_spec_config(pytester)

    pytester.makepyfile("""
        def test_placeholder():
            pass
    """)

    result = pytester.runpytest(
        "--coverage-config=coverage-config.yaml",
        "--coverage-output=out",
    )
    result.assert_outcomes(passed=1)

    result.stdout.fnmatch_lines(
        [
            "*API Coverage Summary (2 specs)*",
            "*auth*/*endpoints*%*req*",
            "*orders*/*endpoints*%*req*",
        ]
    )


def test_multi_spec_totals_row(pytester: pytest.Pytester) -> None:
    """Two-spec run: terminal shows a TOTAL row with aggregate coverage and unmatched count."""
    _write_two_spec_config(pytester)

    pytester.makepyfile("""
        def test_placeholder():
            pass
    """)

    result = pytester.runpytest(
        "--coverage-config=coverage-config.yaml",
        "--coverage-output=out",
    )
    result.assert_outcomes(passed=1)

    result.stdout.fnmatch_lines(
        [
            "*TOTAL*/*endpoints*%*req*unmatched*",
        ]
    )


def test_swagger_backward_compat(pytester: pytest.Pytester) -> None:
    """--swagger mode: produces coverage.json/html/csv (no prefix) and terminal shows API Coverage Summary."""
    spec = pytester.path / "spec.yaml"
    spec.write_text(MINIMAL_SPEC)

    pytester.makeconftest("""
        import pytest
        import httpx

        @pytest.fixture(autouse=True)
        def mock_http(httpx_mock):
            httpx_mock.add_response(url="https://api.example.com/users", status_code=200)
    """)

    pytester.makepyfile("""
        import httpx

        def test_makes_request():
            response = httpx.get("https://api.example.com/users")
            assert response.status_code == 200
    """)

    result = pytester.runpytest(
        "--swagger=spec.yaml",
        "--coverage-output=out",
    )
    result.assert_outcomes(passed=1)

    out = pytester.path / "out"
    assert (out / "coverage.json").exists(), "coverage.json must exist"
    assert (out / "coverage.html").exists(), "coverage.html must exist"
    assert (out / "coverage.csv").exists(), "coverage.csv must exist"
    assert (out / "coverage.json").stat().st_size > 0, "coverage.json must be non-empty"
    assert (out / "coverage.html").stat().st_size > 0, "coverage.html must be non-empty"
    assert (out / "coverage.csv").stat().st_size > 0, "coverage.csv must be non-empty"

    result.stdout.fnmatch_lines(
        [
            "*API Coverage Summary*",
            "*spec*/*endpoints*%*req*",
        ]
    )


def test_split_summary_has_separator(testdir, swagger_file=None):
    """_print_split_summary must produce a write_sep header like other modes."""
    from unittest.mock import MagicMock

    from pytest_api_coverage.plugin import _print_split_summary

    tr = MagicMock()
    report_data = {
        "split_by_origin": True,
        "combined_summary": {
            "covered_endpoints": 1,
            "total_endpoints": 2,
            "coverage_percentage": 50.0,
            "total_requests": 3,
            "origins_count": 1,
        },
        "origins": {
            "https://api.example.com": {
                "summary": {
                    "covered_endpoints": 1,
                    "total_endpoints": 2,
                    "coverage_percentage": 50.0,
                    "total_requests": 3,
                },
            }
        },
    }
    _print_split_summary(tr, report_data)
    tr.write_sep.assert_called_once_with("=", "API Coverage Summary")


def test_swagger_load_failure_shown_in_terminal_summary():
    """When swagger fails to load, terminal summary must show the error."""
    from unittest.mock import MagicMock, patch

    from pytest_api_coverage.plugin import CoverageSinglePlugin

    config = MagicMock()
    config.workerinput = None  # single process mode sentinel check

    settings_mock = MagicMock()
    settings_mock.swagger = "nonexistent.json"
    settings_mock.specs = []
    settings_mock.is_enabled.return_value = True

    with patch("pytest_api_coverage.plugin.CoverageSettings.from_pytest_config", return_value=settings_mock):
        with patch("pytest_api_coverage.plugin.SwaggerParser.parse", side_effect=FileNotFoundError("file not found")):
            plugin = CoverageSinglePlugin(config)
            plugin._load_swagger()

    tr = MagicMock()
    plugin.pytest_terminal_summary(tr)

    tr.write_sep.assert_called_once_with("=", "API Coverage Summary")
    # The written line must mention the error
    written_args = " ".join(str(c) for c in tr.write_line.call_args_list)
    assert "failed" in written_args.lower() or "error" in written_args.lower()


def test_xdist_multi_spec_produces_files(pytester: pytest.Pytester) -> None:
    """Multi-spec run with -n 2 (xdist) produces auth-coverage.json and orders-coverage.html."""
    _write_two_spec_config(pytester)

    pytester.makepyfile("""
        def test_placeholder():
            pass
    """)

    result = pytester.runpytest(
        "--coverage-config=coverage-config.yaml",
        "--coverage-output=out",
        "-n",
        "2",
    )
    result.assert_outcomes(passed=1)

    out = pytester.path / "out"
    assert (out / "auth-coverage.json").exists(), "auth-coverage.json must exist"
    assert (out / "auth-coverage.json").stat().st_size > 0, "auth-coverage.json must be non-empty"
    assert (out / "orders-coverage.html").exists(), "orders-coverage.html must exist"
    assert (out / "orders-coverage.html").stat().st_size > 0, "orders-coverage.html must be non-empty"


def test_zero_requests_captured_shows_warning():
    """When spec loaded OK but no requests captured, terminal summary must warn."""
    from unittest.mock import MagicMock, patch

    from pytest_api_coverage.plugin import CoverageSinglePlugin

    config = MagicMock()
    settings_mock = MagicMock()
    settings_mock.swagger = "swagger.json"
    settings_mock.specs = []
    settings_mock.is_enabled.return_value = True

    swagger_spec_mock = MagicMock()
    collector_mock = MagicMock()
    collector_mock.has_data.return_value = False

    with patch("pytest_api_coverage.plugin.CoverageSettings.from_pytest_config", return_value=settings_mock):
        plugin = CoverageSinglePlugin(config)

    plugin.swagger_spec = swagger_spec_mock
    plugin.collector = collector_mock
    plugin._no_requests_captured = True  # simulate the flag set in pytest_sessionfinish

    tr = MagicMock()
    plugin.pytest_terminal_summary(tr)

    tr.write_sep.assert_called_once_with("=", "API Coverage Summary")
    written_text = " ".join(str(c) for c in tr.write_line.call_args_list)
    assert "0" in written_text or "no" in written_text.lower() or "captured" in written_text.lower()


def test_terminal_summary_omits_html_when_not_requested():
    """When HTML format not requested, terminal summary must not print coverage.html."""
    from pathlib import Path
    from unittest.mock import MagicMock

    from pytest_api_coverage.config.settings import CoverageSettings
    from pytest_api_coverage.plugin import _print_terminal_summary

    tr = MagicMock()
    report_data = {
        "swagger_source": "myapi.yaml",
        "split_by_origin": False,
        "summary": {
            "covered_endpoints": 3,
            "total_endpoints": 5,
            "coverage_percentage": 60.0,
            "total_requests": 10,
        },
        "endpoints": [],
    }
    settings = CoverageSettings(
        swagger=None,
        output_dir=Path("my-reports"),
        formats={"json", "csv"},  # no html
    )
    _print_terminal_summary(tr, report_data, settings)

    written_text = " ".join(str(c) for c in tr.write_line.call_args_list)
    assert "coverage.html" not in written_text
    assert "my-reports" in written_text or "json" in written_text.lower() or "csv" in written_text.lower()


def test_terminal_summary_shows_correct_output_dir():
    """Terminal summary must show the configured output dir, not hardcoded coverage.html."""
    from pathlib import Path
    from unittest.mock import MagicMock

    from pytest_api_coverage.config.settings import CoverageSettings
    from pytest_api_coverage.plugin import _print_terminal_summary

    tr = MagicMock()
    report_data = {
        "swagger_source": "myapi.yaml",
        "split_by_origin": False,
        "summary": {
            "covered_endpoints": 3,
            "total_endpoints": 5,
            "coverage_percentage": 60.0,
            "total_requests": 10,
        },
        "endpoints": [],
    }
    settings = CoverageSettings(
        swagger=None,
        output_dir=Path("custom-reports"),
        formats={"html"},
    )
    _print_terminal_summary(tr, report_data, settings)

    written_text = " ".join(str(c) for c in tr.write_line.call_args_list)
    assert "custom-reports" in written_text
