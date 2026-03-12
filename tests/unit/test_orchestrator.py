"""Unit tests for MultiSpecOrchestrator."""

from __future__ import annotations

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
                urls=["https://auth.example.com"],
                path=auth_spec_file,
            ),
            SpecConfig(
                name="orders",
                urls=["https://orders.example.com"],
                path=orders_spec_file,
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
        """Orchestrator with 2 specs has 2 entries in _reporters."""
        from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

        orch = MultiSpecOrchestrator(settings_two_specs)

        assert len(orch._reporters) == 2
        assert "auth" in orch._reporters
        assert "orders" in orch._reporters

    def test_all_specs_fail_orchestrator_is_noop(self, tmp_path):
        """If _load_all_specs fails for all specs, _specs is empty, generate_all_reports() does nothing."""
        from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

        settings = CoverageSettings(
            specs=[
                SpecConfig(
                    name="bad-spec",
                    urls=["https://bad.example.com"],
                    path=tmp_path / "nonexistent.yaml",
                ),
            ]
        )

        orch = MultiSpecOrchestrator(settings)

        assert orch._specs == []
        assert orch._reporters == {}

        # generate_all_reports() must not raise
        orch.generate_all_reports()

    def test_overlapping_urls_prints_warning(self, auth_spec_file, orders_spec_file, capsys):
        """Two specs share a URL -> warning is printed."""
        from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

        shared_url = "https://api.example.com"
        settings = CoverageSettings(
            specs=[
                SpecConfig(name="auth", urls=[shared_url], path=auth_spec_file),
                SpecConfig(name="orders", urls=[shared_url], path=orders_spec_file),
            ]
        )

        MultiSpecOrchestrator(settings)

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert shared_url in captured.out


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
                SpecConfig(name="auth", urls=[shared_url], path=auth_spec_file),
                SpecConfig(name="orders", urls=[shared_url], path=orders_spec_file),
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
                    urls=["https://api.example.com/auth"],
                    path=auth_spec_file,
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


class TestProcessInteractions:
    def test_process_interactions_routes_correctly(self, settings_two_specs):
        """3 interactions -> 2 auth, 1 orders; each reporter receives only its own."""
        from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

        orch = MultiSpecOrchestrator(settings_two_specs)

        auth_i1 = make_interaction("https://auth.example.com/users")
        auth_i2 = make_interaction("https://auth.example.com/users")
        orders_i1 = make_interaction("https://orders.example.com/users")

        auth_reporter = orch._reporters["auth"]
        orders_reporter = orch._reporters["orders"]

        auth_reporter.process_interactions = MagicMock()
        orders_reporter.process_interactions = MagicMock()

        orch.process_interactions([auth_i1, auth_i2, orders_i1])

        assert auth_reporter.process_interactions.call_count == 2
        assert orders_reporter.process_interactions.call_count == 1

        # Verify each reporter received only its own interaction
        auth_reporter.process_interactions.assert_any_call([auth_i1])
        auth_reporter.process_interactions.assert_any_call([auth_i2])
        orders_reporter.process_interactions.assert_called_once_with([orders_i1])
