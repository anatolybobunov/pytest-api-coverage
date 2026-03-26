"""Unit tests for MultiSpecOrchestrator."""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from hypothesis import given
from hypothesis import strategies as st

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
                api_filters=["https://auth.example.com"],
                swagger_path=auth_spec_file,
            ),
            SpecConfig(
                name="orders",
                api_filters=["https://orders.example.com"],
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
                    api_filters=["https://bad.example.com"],
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
                SpecConfig(name="auth", api_filters=[shared_url], swagger_path=auth_spec_file),
                SpecConfig(name="orders", api_filters=[shared_url], swagger_path=orders_spec_file),
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
                SpecConfig(name="auth", api_filters=[shared_url], swagger_path=auth_spec_file),
                SpecConfig(name="orders", api_filters=[shared_url], swagger_path=orders_spec_file),
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
                    api_filters=["https://api.example.com/auth"],
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
                    api_filters=["http://localhost"],
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


class TestOrchestratorProperties:
    """Property-based tests for MultiSpecOrchestrator using Hypothesis."""

    @given(
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789/-",
            min_size=0,
            max_size=30,
        )
    )
    def test_routing_never_raises(self, path_suffix: str) -> None:
        """route_interaction never raises; always returns str or None."""
        from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

        tmpdir = tempfile.mkdtemp()
        try:
            spec_file = Path(tmpdir) / "spec.yaml"
            spec_file.write_text(MINIMAL_SPEC)
            settings = CoverageSettings(
                specs=[
                    SpecConfig(
                        name="test",
                        api_filters=["https://auth.example.com", "https://orders.example.com"],
                        swagger_path=spec_file,
                    )
                ]
            )
            orch = MultiSpecOrchestrator(settings)
            interaction = {
                "request": {
                    "url": f"https://auth.example.com/{path_suffix}",
                    "method": "GET",
                    "path": f"/{path_suffix}",
                },
                "response": {"status_code": 200},
                "test_name": "test_routing",
            }
            result = orch.route_interaction(interaction)
            assert result is None or isinstance(result, str)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @given(
        st.lists(
            st.sampled_from(
                [
                    "https://auth.example.com/users",
                    "https://auth.example.com/items",
                    "https://orders.example.com/orders",
                    "https://unknown.example.com/path",
                    "https://other.example.com/api",
                ]
            ),
            min_size=0,
            max_size=20,
        )
    )
    def test_unmatched_count_consistency(self, urls: list[str]) -> None:
        """unmatched_count equals the number of interactions that route_interaction returns None for."""
        from pytest_api_coverage.orchestrator import MultiSpecOrchestrator

        tmpdir = tempfile.mkdtemp()
        try:
            spec_file = Path(tmpdir) / "spec.yaml"
            spec_file.write_text(MINIMAL_SPEC)
            settings = CoverageSettings(
                specs=[
                    SpecConfig(name="auth", api_filters=["https://auth.example.com"], swagger_path=spec_file),
                    SpecConfig(name="orders", api_filters=["https://orders.example.com"], swagger_path=spec_file),
                ]
            )
            orch = MultiSpecOrchestrator(settings)

            interactions = [
                {
                    "request": {"url": url, "method": "GET", "path": "/users"},
                    "response": {"status_code": 200},
                    "test_name": "t",
                }
                for url in urls
            ]

            # Pre-compute expected unmatched (route_interaction has no side effects)
            expected_unmatched = sum(1 for i in interactions if orch.route_interaction(i) is None)

            # Mock reporters to avoid reporter side effects
            for reporter in orch.reporters.values():
                reporter.process_interactions = MagicMock()  # type: ignore[method-assign]

            orch.process_interactions(interactions)

            assert orch.unmatched_count == expected_unmatched
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


def test_spec_config_strip_prefixes_field():
    """SpecConfig accepts an optional strip_prefixes list."""
    spec = SpecConfig(
        name="sdb",
        api_filters=["http://symboldb.test.zorg.sh/symboldb"],
        swagger_path=None,
        swagger_url="http://example.com/spec.yaml",
        strip_prefixes=["/symboldb"],
    )
    assert spec.strip_prefixes == ["/symboldb"]


def test_spec_config_strip_prefixes_default():
    """SpecConfig.strip_prefixes defaults to empty list."""
    spec = SpecConfig(
        name="sdb",
        api_filters=["http://symboldb.test.zorg.sh/symboldb"],
        swagger_url="http://example.com/spec.yaml",
    )
    assert spec.strip_prefixes == []


def test_spec_config_serialisation_roundtrip_with_strip_prefixes():
    """SpecConfig.to_dict / from_dict roundtrip preserves strip_prefixes."""
    original = SpecConfig(
        name="sdb",
        api_filters=["http://symboldb.test.zorg.sh/symboldb"],
        swagger_url="http://example.com/spec.yaml",
        strip_prefixes=["/symboldb"],
    )
    restored = SpecConfig.from_dict(original.to_dict())
    assert restored.strip_prefixes == ["/symboldb"]


def test_auto_strip_prefix_from_api_filter(tmp_path):
    """Path prefix in api_filters is auto-stripped when matching request paths."""
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text("""
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
""")
    settings = CoverageSettings(
        specs=[
            SpecConfig(
                name="symboldb",
                api_filters=["http://symboldb.test.zorg.sh/symboldb"],
                swagger_path=spec_file,
            ),
        ]
    )
    from pytest_api_coverage.orchestrator import MultiSpecOrchestrator
    orchestrator = MultiSpecOrchestrator(settings)

    # Request to /symboldb/users should be matched to GET /users in spec
    orchestrator.record_interaction(
        "GET", "http://symboldb.test.zorg.sh/symboldb/users", 200, "test_it"
    )
    report = orchestrator.generate_all_reports()
    summary = report["symboldb"]["summary"]
    assert summary["covered_endpoints"] == 1, "prefix /symboldb should have been stripped"


def test_auto_strip_prefix_not_cross_contaminating(tmp_path):
    """Auto-derived prefix from spec A does NOT strip from spec B requests."""
    sdb_file = tmp_path / "sdb.yaml"
    editor_file = tmp_path / "editor.yaml"
    minimal = """
openapi: "3.0.0"
info:
  title: Test
  version: "1.0"
paths:
  /items:
    get:
      responses:
        "200":
          description: ok
"""
    sdb_file.write_text(minimal)
    editor_file.write_text(minimal)

    settings = CoverageSettings(
        specs=[
            SpecConfig(
                name="symboldb",
                api_filters=["http://symboldb.test.zorg.sh/symboldb"],
                swagger_path=sdb_file,
            ),
            SpecConfig(
                name="symboldb-editor",
                api_filters=["http://symboldb.test.zorg.sh/symboldb-editor"],
                swagger_path=editor_file,
            ),
        ]
    )
    from pytest_api_coverage.orchestrator import MultiSpecOrchestrator
    orchestrator = MultiSpecOrchestrator(settings)

    orchestrator.record_interaction(
        "GET", "http://symboldb.test.zorg.sh/symboldb/items", 200, "test_sdb"
    )
    orchestrator.record_interaction(
        "GET", "http://symboldb.test.zorg.sh/symboldb-editor/items", 200, "test_editor"
    )
    reports = orchestrator.generate_all_reports()
    assert reports["symboldb"]["summary"]["covered_endpoints"] == 1
    assert reports["symboldb-editor"]["summary"]["covered_endpoints"] == 1


def test_explicit_strip_prefixes_respected(tmp_path):
    """Explicit spec.strip_prefixes are used even if api_filters has no path."""
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text("""
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
""")
    settings = CoverageSettings(
        specs=[
            SpecConfig(
                name="sdb",
                api_filters=["http://symboldb.test.zorg.sh"],
                swagger_path=spec_file,
                strip_prefixes=["/symboldb"],
            ),
        ]
    )
    from pytest_api_coverage.orchestrator import MultiSpecOrchestrator
    orchestrator = MultiSpecOrchestrator(settings)
    orchestrator.record_interaction(
        "GET", "http://symboldb.test.zorg.sh/symboldb/users", 200, "test_it"
    )
    report = orchestrator.generate_all_reports()
    assert report["sdb"]["summary"]["covered_endpoints"] == 1
