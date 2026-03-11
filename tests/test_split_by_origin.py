"""Tests for split-by-origin coverage reporting."""

import pytest

from pytest_api_coverage.schemas import SwaggerSpec


@pytest.fixture
def interactions_multi_origin() -> list[dict]:
    """Interactions from multiple origins."""
    return [
        # Origin 1: api.example.com
        {
            "request": {
                "method": "GET",
                "url": "https://api.example.com/api/v1/users",
                "path": "/api/v1/users",
            },
            "response": {"status_code": 200},
            "test_name": "test_api_users",
        },
        {
            "request": {
                "method": "POST",
                "url": "https://api.example.com/api/v1/users",
                "path": "/api/v1/users",
            },
            "response": {"status_code": 201},
            "test_name": "test_api_create",
        },
        # Origin 2: proxy.example.com
        {
            "request": {
                "method": "GET",
                "url": "https://proxy.example.com/api/v1/users",
                "path": "/api/v1/users",
            },
            "response": {"status_code": 200},
            "test_name": "test_proxy_users",
        },
        {
            "request": {
                "method": "GET",
                "url": "https://proxy.example.com/api/v1/users/123",
                "path": "/api/v1/users/123",
            },
            "response": {"status_code": 200},
            "test_name": "test_proxy_user",
        },
        {
            "request": {
                "method": "DELETE",
                "url": "https://proxy.example.com/api/v1/users/456",
                "path": "/api/v1/users/456",
            },
            "response": {"status_code": 204},
            "test_name": "test_proxy_delete",
        },
    ]


class TestSplitByOriginReportStructure:
    """Tests for split-by-origin report structure."""

    def test_split_report_has_correct_keys(
        self,
        simple_swagger_spec: SwaggerSpec,
        interactions_multi_origin: list[dict],
        make_coverage_report,
    ):
        """Split report should have expected top-level keys."""
        report = make_coverage_report(
            simple_swagger_spec, interactions_multi_origin, split_by_origin=True
        )

        assert report["split_by_origin"] is True
        assert "origins" in report
        assert "combined_summary" in report
        assert "summary" not in report  # Standard key should not exist
        assert "endpoints" not in report  # Endpoints are per-origin

    def test_split_report_has_both_origins(
        self,
        simple_swagger_spec: SwaggerSpec,
        interactions_multi_origin: list[dict],
        make_coverage_report,
    ):
        """Split report should contain both origins."""
        report = make_coverage_report(
            simple_swagger_spec, interactions_multi_origin, split_by_origin=True
        )

        origins = report["origins"]
        assert len(origins) == 2
        assert "https://api.example.com" in origins
        assert "https://proxy.example.com" in origins

    def test_origin_has_summary_and_endpoints(
        self,
        simple_swagger_spec: SwaggerSpec,
        interactions_multi_origin: list[dict],
        make_coverage_report,
    ):
        """Each origin should have summary and endpoints."""
        report = make_coverage_report(
            simple_swagger_spec, interactions_multi_origin, split_by_origin=True
        )

        for _origin, origin_data in report["origins"].items():
            assert "summary" in origin_data
            assert "endpoints" in origin_data
            assert "total_endpoints" in origin_data["summary"]
            assert "covered_endpoints" in origin_data["summary"]
            assert "coverage_percentage" in origin_data["summary"]
            assert "total_requests" in origin_data["summary"]


class TestSplitByOriginCoverage:
    """Tests for coverage tracking in split mode."""

    def test_per_origin_coverage_stats(
        self,
        simple_swagger_spec: SwaggerSpec,
        interactions_multi_origin: list[dict],
        make_coverage_report,
    ):
        """Each origin should have independent coverage stats."""
        report = make_coverage_report(
            simple_swagger_spec, interactions_multi_origin, split_by_origin=True
        )

        # api.example.com: GET /users (1), POST /users (1)
        api_summary = report["origins"]["https://api.example.com"]["summary"]
        assert api_summary["total_requests"] == 2
        assert api_summary["covered_endpoints"] == 2

        # proxy.example.com: GET /users (1), GET /users/{id} (1), DELETE /users/{id} (1)
        proxy_summary = report["origins"]["https://proxy.example.com"]["summary"]
        assert proxy_summary["total_requests"] == 3
        assert proxy_summary["covered_endpoints"] == 3

    def test_combined_summary_aggregates(
        self,
        simple_swagger_spec: SwaggerSpec,
        interactions_multi_origin: list[dict],
        make_coverage_report,
    ):
        """Combined summary should aggregate across origins."""
        report = make_coverage_report(
            simple_swagger_spec, interactions_multi_origin, split_by_origin=True
        )

        combined = report["combined_summary"]
        assert combined["total_requests"] == 5  # 2 + 3
        assert combined["origins_count"] == 2
        # covered_endpoints is max across origins = 3
        assert combined["covered_endpoints"] == 3

    def test_all_endpoints_present_per_origin(
        self,
        simple_swagger_spec: SwaggerSpec,
        interactions_multi_origin: list[dict],
        make_coverage_report,
    ):
        """Each origin should have all spec endpoints listed (grouped by path)."""
        report = make_coverage_report(
            simple_swagger_spec, interactions_multi_origin, split_by_origin=True
        )

        for _origin, origin_data in report["origins"].items():
            # 2 paths: /users and /users/{id} (grouped format)
            assert len(origin_data["endpoints"]) == 2
            # total_endpoints in summary (still counts methods, not paths)
            assert origin_data["summary"]["total_endpoints"] == 4


class TestSplitByOriginWithFiltering:
    """Tests for split-by-origin combined with origin filtering."""

    def test_split_with_allowlist(
        self,
        simple_swagger_spec: SwaggerSpec,
        interactions_multi_origin: list[dict],
        make_coverage_report,
    ):
        """Split should respect include_base_urls allowlist."""
        report = make_coverage_report(
            simple_swagger_spec,
            interactions_multi_origin,
            include_base_urls={"https://api.example.com"},
            split_by_origin=True,
        )

        # Only api.example.com should be present
        assert len(report["origins"]) == 1
        assert "https://api.example.com" in report["origins"]

    def test_split_with_base_url(
        self,
        simple_swagger_spec: SwaggerSpec,
        interactions_multi_origin: list[dict],
        make_coverage_report,
    ):
        """Split with single base_url should only have one origin."""
        report = make_coverage_report(
            simple_swagger_spec,
            interactions_multi_origin,
            base_url="https://proxy.example.com",
            split_by_origin=True,
        )

        # Only proxy.example.com
        assert len(report["origins"]) == 1
        assert "https://proxy.example.com" in report["origins"]


class TestSplitByOriginEmptyCase:
    """Tests for split-by-origin with no interactions."""

    def test_empty_split_report(self, simple_swagger_spec: SwaggerSpec, make_coverage_report):
        """Empty interactions should produce valid split report."""
        report = make_coverage_report(simple_swagger_spec, [], split_by_origin=True)

        assert report["split_by_origin"] is True
        assert report["origins"] == {}
        assert report["combined_summary"]["total_endpoints"] == 4
        assert report["combined_summary"]["covered_endpoints"] == 0
        assert report["combined_summary"]["origins_count"] == 0


class TestNonSplitMode:
    """Tests to ensure non-split mode still works correctly."""

    def test_standard_report_structure(
        self,
        simple_swagger_spec: SwaggerSpec,
        interactions_multi_origin: list[dict],
        make_coverage_report,
    ):
        """Standard (non-split) report should have expected keys."""
        report = make_coverage_report(
            simple_swagger_spec, interactions_multi_origin, split_by_origin=False
        )

        assert report["split_by_origin"] is False
        assert "summary" in report
        assert "endpoints" in report
        assert "origins" not in report
        assert "combined_summary" not in report

    def test_standard_aggregates_all_origins(
        self,
        simple_swagger_spec: SwaggerSpec,
        interactions_multi_origin: list[dict],
        make_coverage_report,
    ):
        """Standard mode should aggregate all origins together."""
        report = make_coverage_report(
            simple_swagger_spec, interactions_multi_origin, split_by_origin=False
        )

        # All 5 requests counted
        assert report["summary"]["total_requests"] == 5
        # GET /users (3), POST /users (1), GET /users/{id} (1), DELETE /users/{id} (1)
        assert report["summary"]["covered_endpoints"] == 4
