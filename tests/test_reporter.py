"""Tests for CoverageReporter."""

import tempfile
from pathlib import Path

from pytest_api_coverage.models import EndpointCoverage
from pytest_api_coverage.reporter import CoverageReporter
from pytest_api_coverage.schemas import SwaggerSpec
from pytest_api_coverage.writers import write_reports


class TestEndpointCoverage:
    """Tests for EndpointCoverage dataclass."""

    def test_initial_state(self):
        """Test initial state of EndpointCoverage."""
        endpoint = EndpointCoverage(method="GET", path="/users")

        assert endpoint.method == "GET"
        assert endpoint.path == "/users"
        assert endpoint.hit_count == 0
        assert endpoint.is_covered is False
        assert endpoint.response_codes == {}
        assert endpoint.test_names == set()

    def test_record_hit(self):
        """Test recording a hit on endpoint."""
        endpoint = EndpointCoverage(method="GET", path="/users")
        endpoint.record_hit(200, "test_get_users")

        assert endpoint.hit_count == 1
        assert endpoint.is_covered is True
        assert endpoint.response_codes == {200: 1}
        assert endpoint.test_names == {"test_get_users"}

    def test_multiple_hits_same_status(self):
        """Test multiple hits with same status code."""
        endpoint = EndpointCoverage(method="GET", path="/users")
        endpoint.record_hit(200, "test1")
        endpoint.record_hit(200, "test2")
        endpoint.record_hit(200, "test1")  # Same test again

        assert endpoint.hit_count == 3
        assert endpoint.response_codes == {200: 3}
        assert endpoint.test_names == {"test1", "test2"}

    def test_multiple_status_codes(self):
        """Test multiple status codes (C3 pattern)."""
        endpoint = EndpointCoverage(method="GET", path="/users/{id}")
        endpoint.record_hit(200, "test_found")
        endpoint.record_hit(404, "test_not_found")
        endpoint.record_hit(200, "test_found_again")

        assert endpoint.hit_count == 3
        assert endpoint.response_codes == {200: 2, 404: 1}  # C3: counts per status

    def test_to_dict(self):
        """Test serialization to dict."""
        endpoint = EndpointCoverage(method="POST", path="/users")
        endpoint.record_hit(201, "test_create")

        result = endpoint.to_dict()

        assert result["method"] == "POST"
        assert result["path"] == "/users"
        assert result["hit_count"] == 1
        assert result["is_covered"] is True
        assert result["response_codes"] == {201: 1}
        assert result["test_names"] == ["test_create"]


class TestCoverageReporter:
    """Tests for CoverageReporter."""

    def test_initialization(self, simple_swagger_spec: SwaggerSpec):
        """Test reporter initialization."""
        reporter = CoverageReporter(simple_swagger_spec)

        # Should have all endpoints initialized
        report = reporter.generate_report()
        assert report["summary"]["total_endpoints"] == 4
        assert report["summary"]["covered_endpoints"] == 0

    def test_process_interactions(self, simple_swagger_spec: SwaggerSpec, make_coverage_report):
        """Test processing HTTP interactions."""
        interactions = [
            {
                "request": {"method": "GET", "path": "/api/v1/users"},
                "response": {"status_code": 200},
                "test_name": "test_list_users",
            },
            {
                "request": {"method": "POST", "path": "/api/v1/users"},
                "response": {"status_code": 201},
                "test_name": "test_create_user",
            },
        ]

        report = make_coverage_report(simple_swagger_spec, interactions)

        assert report["summary"]["covered_endpoints"] == 2
        assert report["summary"]["total_requests"] == 2

    def test_path_parameter_matching(self, simple_swagger_spec: SwaggerSpec, make_coverage_report):
        """Test matching paths with parameters."""
        interactions = [
            {
                "request": {"method": "GET", "path": "/api/v1/users/123"},
                "response": {"status_code": 200},
            },
            {
                "request": {"method": "GET", "path": "/api/v1/users/456"},
                "response": {"status_code": 200},
            },
            {
                "request": {"method": "DELETE", "path": "/api/v1/users/abc-xyz"},
                "response": {"status_code": 204},
            },
        ]

        report = make_coverage_report(simple_swagger_spec, interactions)

        # Find /users/{id} path (grouped format)
        path_entry = next(e for e in report["endpoints"] if "{id}" in e["path"])
        assert path_entry["hit_count"] == 3  # Total for path: 2 GET + 1 DELETE

        # Find GET method inside the path
        get_method = next(m for m in path_entry["methods"] if m["method"] == "GET")
        assert get_method["hit_count"] == 2

        # Find DELETE method inside the path
        delete_method = next(m for m in path_entry["methods"] if m["method"] == "DELETE")
        assert delete_method["hit_count"] == 1

    def test_base_path_stripping(self, simple_swagger_spec: SwaggerSpec, make_coverage_report):
        """Test C7: base_path stripping."""
        # Path includes base_path /api/v1
        interactions = [
            {
                "request": {"method": "GET", "path": "/api/v1/users"},
                "response": {"status_code": 200},
            },
        ]

        report = make_coverage_report(simple_swagger_spec, interactions)

        # Find /users path (grouped format)
        path_entry = next(e for e in report["endpoints"] if e["path"] == "/users")
        # Find GET method inside the path
        get_method = next(m for m in path_entry["methods"] if m["method"] == "GET")
        assert get_method["hit_count"] == 1

    def test_no_base_path(self, make_swagger_spec, make_coverage_report):
        """Test matching without base_path."""
        spec = make_swagger_spec(endpoints=[("GET", "/items")], base_path="")

        interactions = [
            {
                "request": {"method": "GET", "path": "/items"},
                "response": {"status_code": 200},
            },
        ]

        report = make_coverage_report(spec, interactions)

        assert report["summary"]["covered_endpoints"] == 1

    def test_unmatched_endpoints_not_covered(self, simple_swagger_spec: SwaggerSpec, make_coverage_report):
        """Test that unmatched paths don't affect coverage."""
        interactions = [
            {
                "request": {"method": "GET", "path": "/api/v1/nonexistent"},
                "response": {"status_code": 404},
            },
        ]

        report = make_coverage_report(simple_swagger_spec, interactions)

        assert report["summary"]["covered_endpoints"] == 0
        assert report["summary"]["total_requests"] == 0

    def test_report_structure(self, simple_swagger_spec: SwaggerSpec):
        """Test report structure (grouped by path)."""
        reporter = CoverageReporter(simple_swagger_spec)
        report = reporter.generate_report()

        # Check summary
        assert "summary" in report
        assert "total_endpoints" in report["summary"]
        assert "covered_endpoints" in report["summary"]
        assert "coverage_percentage" in report["summary"]
        assert "total_requests" in report["summary"]

        # Check endpoints (grouped by path)
        assert "endpoints" in report
        # 2 paths: /users and /users/{id}
        assert len(report["endpoints"]) == 2

        for path_entry in report["endpoints"]:
            # Path-level fields
            assert "path" in path_entry
            assert "hit_count" in path_entry
            assert "is_covered" in path_entry
            assert "all_methods_covered" in path_entry
            assert "methods" in path_entry

            # Method-level fields
            for method_entry in path_entry["methods"]:
                assert "method" in method_entry
                assert "hit_count" in method_entry
                assert "is_covered" in method_entry
                assert "response_codes" in method_entry
                assert "test_names" in method_entry

    def test_endpoints_sorted_by_hit_count(self, simple_swagger_spec: SwaggerSpec, make_coverage_report):
        """Test that paths are sorted by total hit_count descending."""
        interactions = [
            {"request": {"method": "GET", "path": "/api/v1/users"}, "response": {"status_code": 200}},
            {"request": {"method": "GET", "path": "/api/v1/users"}, "response": {"status_code": 200}},
            {"request": {"method": "GET", "path": "/api/v1/users"}, "response": {"status_code": 200}},
            {"request": {"method": "POST", "path": "/api/v1/users"}, "response": {"status_code": 201}},
        ]

        report = make_coverage_report(simple_swagger_spec, interactions)

        # First path should be most hit (total: 3 GET + 1 POST = 4)
        assert report["endpoints"][0]["hit_count"] == 4
        assert report["endpoints"][0]["path"] == "/users"

        # Methods inside are sorted alphabetically
        assert report["endpoints"][0]["methods"][0]["method"] == "GET"
        assert report["endpoints"][0]["methods"][0]["hit_count"] == 3
        assert report["endpoints"][0]["methods"][1]["method"] == "POST"
        assert report["endpoints"][0]["methods"][1]["hit_count"] == 1

    def test_write_reports(self, simple_swagger_spec: SwaggerSpec):
        """Test writing reports in multiple formats."""
        reporter = CoverageReporter(simple_swagger_spec)

        interactions = [
            {"request": {"method": "GET", "path": "/api/v1/users"}, "response": {"status_code": 200}},
        ]
        reporter.process_interactions(interactions)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            written = write_reports(reporter.generate_report(), output_dir, {"json", "csv", "html"})

            assert len(written) == 3
            assert (output_dir / "coverage.json").exists()
            assert (output_dir / "coverage.csv").exists()
            assert (output_dir / "coverage.html").exists()

    def test_write_reports_creates_directory(self, simple_swagger_spec: SwaggerSpec):
        """Test that write_reports creates output directory."""
        reporter = CoverageReporter(simple_swagger_spec)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "nested" / "coverage"
            written = write_reports(reporter.generate_report(), output_dir, {"json"})

            assert output_dir.exists()
            assert len(written) == 1


class TestAmbiguousPathPatterns:
    """Tests for matching when spec has both literal and parameterized paths."""

    def test_literal_path_wins_over_parameter(self, make_swagger_spec, make_coverage_report):
        """GET /users/me should match literal /users/me, not parameterized /users/{id}.

        Even when /users/{id} is listed first in the spec (which would naively match
        /users/me since 'me' satisfies [^/]+), the literal endpoint must take priority.
        """
        spec = make_swagger_spec(
            endpoints=[("GET", "/users/{id}"), ("GET", "/users/me")],
            base_path="",
        )
        interactions = [
            {
                "request": {"method": "GET", "path": "/users/me"},
                "response": {"status_code": 200},
                "test_name": "test_get_me",
            },
        ]
        report = make_coverage_report(spec, interactions)

        me_path = next(e for e in report["endpoints"] if e["path"] == "/users/me")
        me_method = next(m for m in me_path["methods"] if m["method"] == "GET")
        assert me_method["is_covered"] is True, "/users/me endpoint should be covered"

        id_path = next(e for e in report["endpoints"] if e["path"] == "/users/{id}")
        id_method = next(m for m in id_path["methods"] if m["method"] == "GET")
        assert id_method["is_covered"] is False, "/users/{id} should not be covered by /users/me"

    def test_parameterized_path_matches_non_literal(self, make_swagger_spec, make_coverage_report):
        """/users/123 should match /users/{id}, not the literal /users/me."""
        spec = make_swagger_spec(
            endpoints=[("GET", "/users/me"), ("GET", "/users/{id}")],
            base_path="",
        )
        interactions = [
            {
                "request": {"method": "GET", "path": "/users/123"},
                "response": {"status_code": 200},
                "test_name": "test_get_user",
            },
        ]
        report = make_coverage_report(spec, interactions)

        id_path = next(e for e in report["endpoints"] if e["path"] == "/users/{id}")
        id_method = next(m for m in id_path["methods"] if m["method"] == "GET")
        assert id_method["is_covered"] is True, "/users/{id} should be covered by /users/123"

        me_path = next(e for e in report["endpoints"] if e["path"] == "/users/me")
        me_method = next(m for m in me_path["methods"] if m["method"] == "GET")
        assert me_method["is_covered"] is False, "/users/me should not be covered by /users/123"


class TestEdgeCasePaths:
    """Tests documenting edge case path matching behaviors."""

    def test_trailing_slash_in_spec_does_not_match_request_without_slash(self, make_swagger_spec, make_coverage_report):
        """Spec path /users/ (trailing slash) does not match request to /users.

        _normalize_path strips trailing slash from requests, but the spec pattern
        is compiled from the literal spec path (including trailing slash).
        Result: /users regex is ^/users/$ which does not match normalized /users.
        """
        spec = make_swagger_spec(endpoints=[("GET", "/users/")], base_path="")
        interactions = [
            {
                "request": {"method": "GET", "path": "/users"},
                "response": {"status_code": 200},
            },
        ]
        report = make_coverage_report(spec, interactions)

        assert report["summary"]["covered_endpoints"] == 0

    def test_case_sensitive_path_no_match(self, make_swagger_spec, make_coverage_report):
        """Path matching is case-sensitive: /Users/123 does not match /users/{id}."""
        spec = make_swagger_spec(endpoints=[("GET", "/users/{id}")], base_path="")
        interactions = [
            {
                "request": {"method": "GET", "path": "/Users/123"},
                "response": {"status_code": 200},
            },
        ]
        report = make_coverage_report(spec, interactions)

        assert report["summary"]["covered_endpoints"] == 0
        assert report["summary"]["unmatched_requests"] == 1

    def test_case_sensitive_path_correct_case_matches(self, make_swagger_spec, make_coverage_report):
        """Path matching is case-sensitive: correct lowercase /users/123 matches /users/{id}."""
        spec = make_swagger_spec(endpoints=[("GET", "/users/{id}")], base_path="")
        interactions = [
            {
                "request": {"method": "GET", "path": "/users/123"},
                "response": {"status_code": 200},
            },
        ]
        report = make_coverage_report(spec, interactions)

        assert report["summary"]["covered_endpoints"] == 1
