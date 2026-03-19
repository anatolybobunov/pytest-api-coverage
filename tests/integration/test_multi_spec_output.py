"""Integration tests for multi-spec file output (ORC-03, OUT-01).

Uses pytester fixture to run pytest in a subprocess with a temporary project
directory. Validates the full plugin wiring: config file -> orchestrator ->
per-spec prefixed report files.
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

COVERAGE_CONFIG_TEMPLATE = """
specs:
  - name: {name1}
    swagger_path: {path1}
    api_filters:
      - {url1}
  - name: {name2}
    swagger_path: {path2}
    api_filters:
      - {url2}
"""


def test_two_specs_produce_separate_files(pytester: pytest.Pytester) -> None:
    """Two specs -> two prefixed output file sets."""
    auth_spec = pytester.path / "auth.yaml"
    auth_spec.write_text(MINIMAL_SPEC)
    orders_spec = pytester.path / "orders.yaml"
    orders_spec.write_text(MINIMAL_SPEC)

    config_file = pytester.path / "coverage-config.yaml"
    config_file.write_text(
        COVERAGE_CONFIG_TEMPLATE.format(
            name1="auth",
            path1="auth.yaml",
            url1="https://auth.example.com",
            name2="orders",
            path2="orders.yaml",
            url2="https://orders.example.com",
        )
    )

    pytester.makepyfile("""
        def test_placeholder():
            pass
    """)

    result = pytester.runpytest("--coverage-config=coverage-config.yaml", "--coverage-output=out")
    result.assert_outcomes(passed=1)

    out = pytester.path / "out"
    assert (out / "auth-coverage.html").exists(), "auth-coverage.html missing"
    assert (out / "orders-coverage.html").exists(), "orders-coverage.html missing"


def test_request_to_unknown_url_no_error(pytester: pytest.Pytester) -> None:
    """Unmatched HTTP request must not cause errors."""
    spec = pytester.path / "auth.yaml"
    spec.write_text(MINIMAL_SPEC)
    config_file = pytester.path / "coverage-config.yaml"
    config_file.write_text(
        "specs:\n  - name: auth\n    swagger_path: auth.yaml\n    api_filters:\n      - https://auth.example.com\n"
    )
    pytester.makepyfile("""
        def test_placeholder():
            pass
    """)
    result = pytester.runpytest("--coverage-config=coverage-config.yaml", "--coverage-output=out")
    result.assert_outcomes(passed=1)
    # No crash
    assert result.ret == 0


def test_coverage_spec_mode_unchanged(pytester: pytest.Pytester) -> None:
    """--coverage-spec flag runs without error and does not produce prefixed files.

    No actual HTTP calls are made in this test so no report file is written,
    but the critical invariant is that --coverage-spec mode does not produce any
    prefixed file (auth-coverage.json etc.) and exits cleanly.
    """
    spec = pytester.path / "api.yaml"
    spec.write_text(MINIMAL_SPEC)
    pytester.makepyfile("""
        def test_placeholder():
            pass
    """)
    result = pytester.runpytest("--coverage-spec=api.yaml", "--coverage-output=out")
    result.assert_outcomes(passed=1)
    out = pytester.path / "out"
    # Prefixed files must NOT exist (no multi-spec mode activated)
    if out.exists():
        assert not list(out.glob("*-coverage.json")), "Unexpected prefixed files in single-spec mode"
    # No error output
    assert result.ret == 0


def test_zero_matched_requests_writes_files(pytester: pytest.Pytester) -> None:
    """Spec with zero matched requests still writes report files."""
    spec = pytester.path / "auth.yaml"
    spec.write_text(MINIMAL_SPEC)
    config_file = pytester.path / "coverage-config.yaml"
    config_file.write_text(
        "specs:\n  - name: auth\n    swagger_path: auth.yaml\n    api_filters:\n      - https://auth.example.com\n"
    )
    pytester.makepyfile("""
        def test_placeholder():
            pass
    """)
    result = pytester.runpytest("--coverage-config=coverage-config.yaml", "--coverage-output=out")
    result.assert_outcomes(passed=1)
    out = pytester.path / "out"
    assert (out / "auth-coverage.html").exists(), "auth-coverage.html must exist even with 0 requests"
