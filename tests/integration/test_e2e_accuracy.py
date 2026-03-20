"""E2E pipeline accuracy: request → collector → reporter → JSON → exact numbers.

These tests verify that coverage numbers in reports are correct end-to-end,
not just that files are created or terminal output is non-empty.
"""
from __future__ import annotations

import json

import pytest


ACCURACY_SPEC = """
openapi: "3.0.0"
info:
  title: Accuracy Test API
  version: "1.0"
paths:
  /items:
    get:
      responses:
        "200":
          description: ok
    post:
      responses:
        "201":
          description: created
  /items/{id}:
    get:
      responses:
        "200":
          description: ok
    delete:
      responses:
        "204":
          description: deleted
"""


def test_exact_coverage_numbers(pytester: pytest.Pytester) -> None:
    """2 of 4 endpoints hit → JSON shows total=4, covered=2, percentage=50.0."""
    (pytester.path / "api.yaml").write_text(ACCURACY_SPEC)

    pytester.makepyfile("""
        import httpx

        def test_get_items(httpx_mock):
            httpx_mock.add_response(url="https://api.example.com/items", status_code=200)
            httpx.get("https://api.example.com/items")

        def test_get_item(httpx_mock):
            httpx_mock.add_response(url="https://api.example.com/items/42", status_code=200)
            httpx.get("https://api.example.com/items/42")
    """)

    result = pytester.runpytest(
        "--coverage-spec=api.yaml",
        "--coverage-output=out",
        "--coverage-format=json",
    )
    result.assert_outcomes(passed=2)

    data = json.loads((pytester.path / "out" / "coverage.json").read_text())
    summary = data["summary"]

    assert summary["total_endpoints"] == 4
    assert summary["covered_endpoints"] == 2
    assert summary["coverage_percentage"] == 50.0
    assert summary["total_requests"] == 2


def test_hit_count_accumulates_across_tests(pytester: pytest.Pytester) -> None:
    """Same endpoint hit across multiple tests → hit_count accumulates correctly."""
    (pytester.path / "api.yaml").write_text(ACCURACY_SPEC)

    pytester.makepyfile("""
        import httpx

        def test_first(httpx_mock):
            httpx_mock.add_response(url="https://api.example.com/items", status_code=200)
            httpx.get("https://api.example.com/items")

        def test_second(httpx_mock):
            httpx_mock.add_response(url="https://api.example.com/items", status_code=200)
            httpx.get("https://api.example.com/items")

        def test_third(httpx_mock):
            httpx_mock.add_response(url="https://api.example.com/items", status_code=200)
            httpx.get("https://api.example.com/items")
    """)

    result = pytester.runpytest(
        "--coverage-spec=api.yaml",
        "--coverage-output=out",
        "--coverage-format=json",
    )
    result.assert_outcomes(passed=3)

    data = json.loads((pytester.path / "out" / "coverage.json").read_text())

    items_path = next(e for e in data["endpoints"] if e["path"] == "/items")
    get_method = next(m for m in items_path["methods"] if m["method"] == "GET")

    assert get_method["hit_count"] == 3
    assert get_method["is_covered"] is True


def test_unmatched_requests_not_counted_as_covered(pytester: pytest.Pytester) -> None:
    """Requests to paths not in spec count as unmatched, not as covered endpoints."""
    (pytester.path / "api.yaml").write_text(ACCURACY_SPEC)

    pytester.makepyfile("""
        import httpx

        def test_unknown_path(httpx_mock):
            httpx_mock.add_response(url="https://api.example.com/nonexistent", status_code=404)
            httpx.get("https://api.example.com/nonexistent")
    """)

    result = pytester.runpytest(
        "--coverage-spec=api.yaml",
        "--coverage-output=out",
        "--coverage-format=json",
    )
    result.assert_outcomes(passed=1)

    data = json.loads((pytester.path / "out" / "coverage.json").read_text())
    summary = data["summary"]

    assert summary["covered_endpoints"] == 0
    assert summary["total_requests"] == 0
    assert summary["unmatched_requests"] == 1
