"""Integration tests for explicit --coverage-config flag and plugin inactive state.

These tests use the pytester fixture (pytest >= 7.0 built-in) to run pytest in a
subprocess with a temporary project directory.
"""

from __future__ import annotations

import pytest

# Minimal OpenAPI YAML content for spec path validation to pass
_MINIMAL_OPENAPI = "openapi: '3.0.0'\ninfo:\n  title: Test\n  version: '1.0'\npaths: {}\n"

# Valid coverage-config.yaml content with one spec (path-based)
_COVERAGE_CONFIG_ONE_SPEC = """\
specs:
  - name: auth
    swagger_path: ./auth.yaml
    api_filters:
      - https://auth.example.com
"""

# Valid coverage-config.json content with one spec (url-based, no path validation needed)
_COVERAGE_CONFIG_JSON_ONE_SPEC = """\
{
  "specs": [
    {
      "name": "orders",
      "swagger_url": "https://orders.example.com/openapi.json",
      "api_filters": ["https://orders.example.com"]
    }
  ]
}
"""


def test_no_flags_plugin_inactive(pytester: pytest.Pytester) -> None:
    """No CLI spec flags -> plugin is inactive, no error.

    The plugin should fall through silently (disabled state) even if config files
    are present in the project root.
    """
    # Place a coverage-config.yaml to verify it is NOT auto-discovered
    pytester.makefile(".yaml", **{"coverage-config": _COVERAGE_CONFIG_ONE_SPEC})
    pytester.makefile(".yaml", **{"auth": _MINIMAL_OPENAPI})
    pytester.makepyfile("def test_noop(): pass")

    result = pytester.runpytest("--collect-only", "-q")

    # No api-coverage errors at all
    result.stdout.no_fnmatch_line("*api-coverage*error*")
    result.stdout.no_fnmatch_line("*Config file not found*")
    assert result.ret == 0


def test_explicit_coverage_config(pytester: pytest.Pytester) -> None:
    """Explicit --coverage-config=path loads specs from the specified file.

    When the path exists and is valid, specs are loaded and the run proceeds.
    """
    # Put the config file in a non-default location
    pytester.makefile(".yaml", **{"my-api-config": _COVERAGE_CONFIG_ONE_SPEC})
    pytester.makefile(".yaml", **{"auth": _MINIMAL_OPENAPI})
    pytester.makepyfile("def test_noop(): pass")

    result = pytester.runpytest("--coverage-config=my-api-config.yaml", "--collect-only", "-q")

    result.stdout.no_fnmatch_line("*Config file not found*")
    result.stdout.no_fnmatch_line("*Spec file not found*")
    assert result.ret == 0


def test_explicit_coverage_config_missing_file(pytester: pytest.Pytester) -> None:
    """--coverage-config pointing to a non-existent file triggers pytest.exit().

    The run should abort with non-zero exit code and a clear error message
    containing 'Config file not found'.
    """
    pytester.makepyfile("def test_noop(): pass")

    result = pytester.runpytest("--coverage-config=nonexistent.yaml", "--collect-only", "-q")

    assert result.ret != 0
    # pytest.exit() writes the message to stderr as "Exit: <message>"
    result.stderr.fnmatch_lines(["*Config file not found*"])
