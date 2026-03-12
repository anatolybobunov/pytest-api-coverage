"""Integration tests for config file auto-discovery and explicit --coverage-config flag.

These tests use the pytester fixture (pytest >= 7.0 built-in) to run pytest in a
subprocess with a temporary project directory. This validates the full activation
path: config file found -> parsed -> specs in CoverageSettings -> is_enabled() True.
"""

from __future__ import annotations

import pytest

# Minimal OpenAPI YAML content for spec path validation to pass
_MINIMAL_OPENAPI = "openapi: '3.0.0'\ninfo:\n  title: Test\n  version: '1.0'\npaths: {}\n"

# Valid coverage-config.yaml content with one spec (path-based)
_COVERAGE_CONFIG_ONE_SPEC = """\
specs:
  - name: auth
    path: ./auth.yaml
    urls:
      - https://auth.example.com
"""

# Valid coverage-config.json content with one spec (url-based, no path validation needed)
_COVERAGE_CONFIG_JSON_ONE_SPEC = """\
{
  "specs": [
    {
      "name": "orders",
      "url": "https://orders.example.com/openapi.json",
      "urls": ["https://orders.example.com"]
    }
  ]
}
"""


def test_autodiscover_yaml(pytester: pytest.Pytester) -> None:
    """Auto-discovery finds coverage-config.yaml in project root and loads specs.

    The plugin should discover coverage-config.yaml, load the spec, validate the
    spec's path (auth.yaml) exists, and proceed without error.
    """
    # Create the coverage-config.yaml in the temp project root
    pytester.makefile(".yaml", **{"coverage-config": _COVERAGE_CONFIG_ONE_SPEC})
    # Create the spec file so path validation passes
    pytester.makefile(".yaml", **{"auth": _MINIMAL_OPENAPI})
    # Create a dummy test
    pytester.makepyfile("def test_noop(): pass")

    result = pytester.runpytest("--collect-only", "-q")

    # Plugin should not exit with a config error
    result.stdout.no_fnmatch_line("*Config file not found*")
    result.stdout.no_fnmatch_line("*Spec file not found*")
    assert result.ret == 0


def test_autodiscover_json(pytester: pytest.Pytester) -> None:
    """Auto-discovery finds coverage-config.json when no YAML present.

    When only coverage-config.json exists, the plugin loads it silently.
    Uses url-based spec entry to avoid path validation.
    """
    pytester.makefile(".json", **{"coverage-config": _COVERAGE_CONFIG_JSON_ONE_SPEC})
    pytester.makepyfile("def test_noop(): pass")

    result = pytester.runpytest("--collect-only", "-q")

    result.stdout.no_fnmatch_line("*Config file not found*")
    result.stdout.no_fnmatch_line("*Spec file not found*")
    assert result.ret == 0


def test_autodiscover_both_yaml_wins(pytester: pytest.Pytester) -> None:
    """When both coverage-config.yaml and coverage-config.json exist, YAML wins.

    A warning is printed to indicate the YAML file was chosen over JSON.
    """
    pytester.makefile(".yaml", **{"coverage-config": _COVERAGE_CONFIG_ONE_SPEC})
    pytester.makefile(".json", **{"coverage-config": _COVERAGE_CONFIG_JSON_ONE_SPEC})
    pytester.makefile(".yaml", **{"auth": _MINIMAL_OPENAPI})
    pytester.makepyfile("def test_noop(): pass")

    result = pytester.runpytest("--collect-only", "-q")

    # Warning about both files being present should appear
    result.stdout.fnmatch_lines(["*coverage-config.yaml*", "*YAML*"])
    assert result.ret == 0


def test_autodiscover_none_no_flag_falls_through(pytester: pytest.Pytester) -> None:
    """No config file and no CLI spec flags -> plugin is inactive, no error.

    The plugin should fall through silently to --swagger mode (disabled state).
    """
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
