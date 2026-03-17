"""Unit tests for MultiSpecOrchestrator."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pytest_api_coverage.config.settings import CoverageSettings, SpecConfig

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


@pytest.fixture
def auth_spec_file(tmp_path):
    f = tmp_path / "auth.yaml"
    f.write_text(MINIMAL_SPEC)
    return f


@pytest.fixture
def orders_spec_file(tmp_path):
    f = tmp_path / "orders.yaml"
    f.write_text(MINIMAL_SPEC)
    return f


@pytest.fixture
def settings_two_specs(auth_spec_file, orders_spec_file):
    """CoverageSettings with two specs: auth and orders."""
    return CoverageSettings(
        specs=[
            SpecConfig(
                name="auth",
                api_urls=["https://auth.example.com"],
                swagger_path=auth_spec_file,
            ),
            SpecConfig(
                name="orders",
                api_urls=["https://orders.example.com"],
                swagger_path=orders_spec_file,
            ),
        ]
    )


def make_interaction(url: str, method: str = "GET", path: str = "/users") -> dict:
    return {
        "request": {"url": url, "method": method, "path": path},
        "response": {"status_code": 200},
        "test_name": "test_something",
    }


class TestMultiSpecOrchestratorInit:
    def test_init_creates_reporter_per_spec(self, settings_two_specs):
        """Orchestrator with 2 specs has 2 entries in reporters."""
        from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

        orch = MultiSpecOrchestrator(settings_two_specs)

        assert len(orch.reporters) == 2
        assert "auth" in orch.reporters
        assert "orders" in orch.reporters

    def test_all_specs_fail_orchestrator_is_noop(self, tmp_path):
        """If _load_all_specs fails for all specs, _specs is empty, generate_all_reports() does nothing."""
        from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

        settings = CoverageSettings(
            specs=[
                SpecConfig(
                    name="bad-spec",
                    api_urls=["https://bad.example.com"],
                    swagger_path=tmp_path / "nonexistent.yaml",
                ),
            ]
        )

        orch = MultiSpecOrchestrator(settings)

        assert orch.specs == []
        assert orch.reporters == {}

        # generate_all_reports() must not raise
        orch.generate_all_reports()

    def test_overlapping_urls_prints_warning(self, auth_spec_file, orders_spec_file, caplog):
        """Two specs share a URL -> warning is logged."""
        import logging

        from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

        shared_url = "https://api.example.com"
        settings = CoverageSettings(
            specs=[
                SpecConfig(name="auth", api_urls=[shared_url], swagger_path=auth_spec_file),
                SpecConfig(name="orders", api_urls=[shared_url], swagger_path=orders_spec_file),
            ]
        )

        with caplog.at_level(logging.WARNING, logger="pytest_api_coverage"):
            MultiSpecOrchestrator(settings)

        assert shared_url in caplog.text


class TestRouteInteraction:
    def test_route_interaction_matches_correct_spec(self, settings_two_specs):
        """Request to auth URL -> 'auth'; request to orders URL -> 'orders'."""
        from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

        orch = MultiSpecOrchestrator(settings_two_specs)

        auth_interaction = make_interaction("https://auth.example.com/users")
        orders_interaction = make_interaction("https://orders.example.com/users")

        assert orch.route_interaction(auth_interaction) == "auth"
        assert orch.route_interaction(orders_interaction) == "orders"

    def test_route_interaction_first_match_wins(self, auth_spec_file, orders_spec_file):
        """Request matches both specs (overlapping URLs) -> first spec wins."""
        from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

        shared_url = "https://api.example.com"
        settings = CoverageSettings(
            specs=[
                SpecConfig(name="auth", api_urls=[shared_url], swagger_path=auth_spec_file),
                SpecConfig(name="orders", api_urls=[shared_url], swagger_path=orders_spec_file),
            ]
        )

        orch = MultiSpecOrchestrator(settings)
        interaction = make_interaction("https://api.example.com/users")

        # First spec ("auth") should win
        result = orch.route_interaction(interaction)
        assert result == "auth"

    def test_route_interaction_no_match_returns_none(self, settings_two_specs):
        """Request to unknown origin -> None."""
        from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

        orch = MultiSpecOrchestrator(settings_two_specs)
        interaction = make_interaction("https://unknown.example.com/users")

        result = orch.route_interaction(interaction)
        assert result is None

    def test_route_interaction_path_prefix(self, auth_spec_file):
        """Spec URL https://api.example.com/auth matches /auth/users but NOT /authentic."""
        from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

        settings = CoverageSettings(
            specs=[
                SpecConfig(
                    name="auth",
                    api_urls=["https://api.example.com/auth"],
                    swagger_path=auth_spec_file,
                ),
            ]
        )

        orch = MultiSpecOrchestrator(settings)

        # /auth/users should match
        match_interaction = make_interaction("https://api.example.com/auth/users", path="/auth/users")
        assert orch.route_interaction(match_interaction) == "auth"

        # /authentic should NOT match (partial segment)
        no_match_interaction = make_interaction("https://api.example.com/authentic", path="/authentic")
        assert orch.route_interaction(no_match_interaction) is None


class TestUnmatchedCounter:
    def test_unmatched_increments_counter(self, settings_two_specs):
        """Unmatched interaction increments orchestrator.unmatched_count."""
        from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

        orch = MultiSpecOrchestrator(settings_two_specs)
        assert orch.unmatched_count == 0

        unknown_interaction = make_interaction("https://unknown.example.com/users")
        orch.process_interactions([unknown_interaction, unknown_interaction])

        assert orch.unmatched_count == 2


class TestSpecLoadExcInfo:
    def test_failed_spec_load_includes_traceback_in_log(self, tmp_path: Path, caplog) -> None:
        """When a spec fails to load, exc_info must be present in the log record."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text(": invalid: yaml [unclosed", encoding="utf-8")

        settings = CoverageSettings(
            specs=[
                SpecConfig(
                    name="bad-api",
                    api_urls=["http://localhost"],
                    swagger_path=bad_yaml,
                )
            ]
        )

        with caplog.at_level(logging.WARNING, logger="pytest_api_coverage"):
            from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

            MultiSpecOrchestrator(settings)

        assert any(r.exc_info is not None for r in caplog.records), (
            "Expected exc_info in log record — add exc_info=True to logger.warning in _load_all_specs"
        )


class TestProcessInteractions:
    def test_process_interactions_routes_correctly(self, settings_two_specs):
        """3 interactions -> 2 auth, 1 orders; each reporter receives only its own."""
        from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

        orch = MultiSpecOrchestrator(settings_two_specs)

        auth_i1 = make_interaction("https://auth.example.com/users")
        auth_i2 = make_interaction("https://auth.example.com/users")
        orders_i1 = make_interaction("https://orders.example.com/users")

        auth_reporter = orch.reporters["auth"]
        orders_reporter = orch.reporters["orders"]

        auth_reporter.process_interactions = MagicMock()
        orders_reporter.process_interactions = MagicMock()

        orch.process_interactions([auth_i1, auth_i2, orders_i1])

        assert auth_reporter.process_interactions.call_count == 2
        assert orders_reporter.process_interactions.call_count == 1

        # Verify each reporter received only its own interaction
        auth_reporter.process_interactions.assert_any_call([auth_i1])
        auth_reporter.process_interactions.assert_any_call([auth_i2])
        orders_reporter.process_interactions.assert_called_once_with([orders_i1])
