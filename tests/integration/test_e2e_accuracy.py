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


MULTI_PARAM_SPEC = """
openapi: "3.0.0"
info:
  title: Multi Param API
  version: "1.0"
paths:
  /users/{id}/posts/{post_id}:
    get:
      responses:
        "200":
          description: ok
    delete:
      responses:
        "204":
          description: deleted
"""


def test_multi_param_path_hit_count(pytester: pytest.Pytester) -> None:
    """Path with 2+ parameters matches correctly and accumulates hit_count."""
    (pytester.path / "api.yaml").write_text(MULTI_PARAM_SPEC)

    pytester.makepyfile("""
        import httpx

        def test_hits(httpx_mock):
            for uid, pid in [("1", "10"), ("2", "20"), ("3", "30")]:
                url = f"https://api.example.com/users/{uid}/posts/{pid}"
                httpx_mock.add_response(url=url, status_code=200)
                httpx.get(url)
    """)

    result = pytester.runpytest(
        "--coverage-spec=api.yaml",
        "--coverage-output=out",
        "--coverage-format=json",
    )
    result.assert_outcomes(passed=1)

    data = json.loads((pytester.path / "out" / "coverage.json").read_text())
    summary = data["summary"]
    endpoint = next(e for e in data["endpoints"] if e["path"] == "/users/{id}/posts/{post_id}")
    get_method = next(m for m in endpoint["methods"] if m["method"] == "GET")

    assert get_method["hit_count"] == 3
    assert summary["covered_endpoints"] == 1
    assert summary["total_requests"] == 3


PRIORITY_SPEC = """
openapi: "3.0.0"
info:
  title: Priority Test API
  version: "1.0"
paths:
  /users/me:
    get:
      responses:
        "200":
          description: ok
  /users/{id}:
    get:
      responses:
        "200":
          description: ok
"""


def test_literal_path_not_shadowed_by_parameterized(pytester: pytest.Pytester) -> None:
    """/users/me is not captured by /users/{id} — literal paths have priority."""
    (pytester.path / "api.yaml").write_text(PRIORITY_SPEC)

    pytester.makepyfile("""
        import httpx

        def test_me(httpx_mock):
            httpx_mock.add_response(url="https://api.example.com/users/me", status_code=200)
            httpx.get("https://api.example.com/users/me")

        def test_by_id(httpx_mock):
            httpx_mock.add_response(url="https://api.example.com/users/123", status_code=200)
            httpx.get("https://api.example.com/users/123")
    """)

    result = pytester.runpytest(
        "--coverage-spec=api.yaml",
        "--coverage-output=out",
        "--coverage-format=json",
    )
    result.assert_outcomes(passed=2)

    data = json.loads((pytester.path / "out" / "coverage.json").read_text())
    me_endpoint = next(e for e in data["endpoints"] if e["path"] == "/users/me")
    id_endpoint = next(e for e in data["endpoints"] if e["path"] == "/users/{id}")

    me_get = next(m for m in me_endpoint["methods"] if m["method"] == "GET")
    id_get = next(m for m in id_endpoint["methods"] if m["method"] == "GET")

    assert me_get["hit_count"] == 1
    assert id_get["hit_count"] == 1


ITEMS_ID_SPEC = """
openapi: "3.0.0"
info:
  title: Status Codes API
  version: "1.0"
paths:
  /items/{id}:
    get:
      responses:
        "200":
          description: ok
        "404":
          description: not found
        "500":
          description: error
"""


def test_same_endpoint_different_status_codes(pytester: pytest.Pytester) -> None:
    """hit_count sums all responses; response_codes breakdown is present in JSON."""
    (pytester.path / "api.yaml").write_text(ITEMS_ID_SPEC)

    pytester.makepyfile("""
        import httpx

        def test_responses(httpx_mock):
            for status in [200, 200, 404, 500]:
                httpx_mock.add_response(
                    url="https://api.example.com/items/1", status_code=status
                )
                httpx.get("https://api.example.com/items/1")
    """)

    result = pytester.runpytest(
        "--coverage-spec=api.yaml",
        "--coverage-output=out",
        "--coverage-format=json",
    )
    result.assert_outcomes(passed=1)

    data = json.loads((pytester.path / "out" / "coverage.json").read_text())
    endpoint = next(e for e in data["endpoints"] if e["path"] == "/items/{id}")
    get_method = next(m for m in endpoint["methods"] if m["method"] == "GET")

    assert get_method["hit_count"] == 4
    assert get_method["is_covered"] is True


METHODS_SPEC = """
openapi: "3.0.0"
info:
  title: Methods API
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
"""


def test_multiple_methods_same_path_counted_independently(pytester: pytest.Pytester) -> None:
    """GET and POST on /items are counted independently."""
    (pytester.path / "api.yaml").write_text(METHODS_SPEC)

    pytester.makepyfile("""
        import httpx

        def test_gets(httpx_mock):
            for _ in range(3):
                httpx_mock.add_response(url="https://api.example.com/items", status_code=200)
                httpx.get("https://api.example.com/items")

        def test_posts(httpx_mock):
            for _ in range(2):
                httpx_mock.add_response(url="https://api.example.com/items", status_code=201)
                httpx.post("https://api.example.com/items")
    """)

    result = pytester.runpytest(
        "--coverage-spec=api.yaml",
        "--coverage-output=out",
        "--coverage-format=json",
    )
    result.assert_outcomes(passed=2)

    data = json.loads((pytester.path / "out" / "coverage.json").read_text())
    endpoint = next(e for e in data["endpoints"] if e["path"] == "/items")
    get_method = next(m for m in endpoint["methods"] if m["method"] == "GET")
    post_method = next(m for m in endpoint["methods"] if m["method"] == "POST")

    assert get_method["hit_count"] == 3
    assert post_method["hit_count"] == 2
    assert data["summary"]["total_requests"] == 5


THREE_ENDPOINT_SPEC = """
openapi: "3.0.0"
info:
  title: Zero Hits API
  version: "1.0"
paths:
  /a:
    get:
      responses:
        "200":
          description: ok
  /b:
    get:
      responses:
        "200":
          description: ok
  /c:
    get:
      responses:
        "200":
          description: ok
"""


def test_zero_hits_remain_uncovered(pytester: pytest.Pytester) -> None:
    """Endpoints never called have hit_count == 0 and is_covered == False."""
    (pytester.path / "api.yaml").write_text(THREE_ENDPOINT_SPEC)

    pytester.makepyfile("""
        import httpx

        def test_only_a(httpx_mock):
            httpx_mock.add_response(url="https://api.example.com/a", status_code=200)
            httpx.get("https://api.example.com/a")
    """)

    result = pytester.runpytest(
        "--coverage-spec=api.yaml",
        "--coverage-output=out",
        "--coverage-format=json",
    )
    result.assert_outcomes(passed=1)

    data = json.loads((pytester.path / "out" / "coverage.json").read_text())

    for path in ["/b", "/c"]:
        endpoint = next(e for e in data["endpoints"] if e["path"] == path)
        get_method = next(m for m in endpoint["methods"] if m["method"] == "GET")
        assert get_method["hit_count"] == 0
        assert get_method["is_covered"] is False


def test_duplicate_calls_in_single_test(pytester: pytest.Pytester) -> None:
    """All N calls within a single test function are counted toward hit_count."""
    (pytester.path / "api.yaml").write_text(ACCURACY_SPEC)

    pytester.makepyfile("""
        import httpx

        def test_five_calls(httpx_mock):
            for _ in range(5):
                httpx_mock.add_response(
                    url="https://api.example.com/items", status_code=200
                )
                httpx.get("https://api.example.com/items")
    """)

    result = pytester.runpytest(
        "--coverage-spec=api.yaml",
        "--coverage-output=out",
        "--coverage-format=json",
    )
    result.assert_outcomes(passed=1)

    data = json.loads((pytester.path / "out" / "coverage.json").read_text())
    endpoint = next(e for e in data["endpoints"] if e["path"] == "/items")
    get_method = next(m for m in endpoint["methods"] if m["method"] == "GET")

    assert get_method["hit_count"] == 5
