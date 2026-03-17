"""Full acceptance integration tests for pytest-api-coverage plugin.

These tests demonstrate the complete workflow:
1. Parse Swagger specification
2. Execute HTTP requests against mock server
3. Generate coverage reports in all formats
4. Verify report contents match expected coverage

Reports are saved to `api-coverage-report/` for visual inspection.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
import requests
import responses

from pytest_api_coverage.adapters.requests_adapter import RequestsAdapter
from pytest_api_coverage.collector import CoverageCollector
from pytest_api_coverage.reporter import CoverageReporter
from pytest_api_coverage.schemas import SwaggerParser
from pytest_api_coverage.writers import CsvWriter, HtmlWriter, JsonWriter

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def swagger_spec():
    """Load swagger specification from test fixture."""
    swagger_path = Path(__file__).parent / "test_data" / "swagger_test.json"
    return SwaggerParser.parse(swagger_path)


@pytest.fixture
def output_dir() -> Path:
    """Output directory for reports."""
    output = Path(__file__).parent.parent / "api-coverage-report"
    output.mkdir(parents=True, exist_ok=True)
    return output


@pytest.fixture
def mock_api():
    """Setup mock API responses for all endpoints."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        # GET /get - multiple calls allowed with different responses
        rsps.add(
            responses.GET,
            "http://mock-api.local/get",
            json={"method": "GET", "data": "test"},
            status=200,
        )
        rsps.add(
            responses.GET,
            "http://mock-api.local/get",
            json={"method": "GET", "data": "test2"},
            status=200,
        )
        rsps.add(
            responses.GET,
            "http://mock-api.local/get",
            json={"method": "GET", "data": "test3"},
            status=200,
        )
        rsps.add(
            responses.GET,
            "http://mock-api.local/get",
            json={"error": "not found"},
            status=404,
        )
        # POST /post - returns 201
        rsps.add(
            responses.POST,
            "http://mock-api.local/post",
            json={"method": "POST", "created": True},
            status=201,
        )
        # PUT /put - returns 200
        rsps.add(
            responses.PUT,
            "http://mock-api.local/put",
            json={"method": "PUT", "updated": True},
            status=200,
        )
        # DELETE /delete - returns 204 (no content)
        rsps.add(
            responses.DELETE,
            "http://mock-api.local/delete",
            status=204,
        )
        yield rsps


@pytest.fixture
def collector_with_adapter():
    """Setup collector with requests adapter installed."""
    collector = CoverageCollector()
    adapter = RequestsAdapter(collector)
    adapter.install()
    yield collector
    adapter.uninstall()


# ============================================================================
# Integration Tests
# ============================================================================


class TestFullCoverageWorkflow:
    """Full acceptance tests for coverage workflow."""

    @pytest.mark.parametrize(
        "report_format,writer_class,filename,content_check",
        [
            pytest.param(
                "json",
                JsonWriter,
                "integration_coverage.json",
                lambda p: json.loads(p.read_text()),
                id="JSON report",
            ),
            pytest.param(
                "csv",
                CsvWriter,
                "integration_coverage.csv",
                lambda p: list(csv.DictReader(open(p))),
                id="CSV report",
            ),
            pytest.param(
                "html",
                HtmlWriter,
                "integration_coverage.html",
                lambda p: p.read_text(),
                id="HTML report",
            ),
        ],
    )
    def test_full_coverage_report_generation(
        self,
        mock_api,
        collector_with_adapter,
        swagger_spec,
        output_dir,
        report_format,
        writer_class,
        filename,
        content_check,
    ):
        """Test complete coverage workflow with parameterized output formats.

        This test:
        1. Makes HTTP requests to mock server (covering some endpoints)
        2. Collects HTTP interactions
        3. Generates coverage report
        4. Writes report to file
        5. Verifies report contents
        """
        collector = collector_with_adapter

        # Set test name for attribution
        collector.set_current_test("test_full_coverage_report_generation")

        # Make requests to mock API - partial coverage
        # Cover GET (multiple times with different status codes)
        response = requests.get("http://mock-api.local/get")
        assert response.status_code == 200

        response = requests.get("http://mock-api.local/get")
        assert response.status_code == 200

        response = requests.get("http://mock-api.local/get")
        assert response.status_code == 200

        response = requests.get("http://mock-api.local/get")
        assert response.status_code == 404

        # Cover POST
        response = requests.post("http://mock-api.local/post", json={"name": "test"})
        assert response.status_code == 201

        # Don't cover PUT and DELETE - to show partial coverage

        # Generate report
        reporter = CoverageReporter(swagger_spec)
        reporter.process_interactions(collector.get_data())
        report_data = reporter.generate_report()

        # Write report to file
        output_path = output_dir / filename
        writer_class.write(report_data, output_path)

        # Verify file exists
        assert output_path.exists(), f"Report file not created: {output_path}"

        # Verify report contents
        content = content_check(output_path)

        if report_format == "json":
            assert content["summary"]["total_endpoints"] == 4
            assert content["summary"]["covered_endpoints"] == 2
            assert content["summary"]["coverage_percentage"] == 50.0
            assert content["summary"]["total_requests"] == 5

            # Check /get path has GET method with multiple response codes (grouped format)
            get_path = next(e for e in content["endpoints"] if e["path"] == "/get")
            assert get_path["hit_count"] == 4  # Total for path
            get_method = next(m for m in get_path["methods"] if m["method"] == "GET")
            assert get_method["hit_count"] == 4
            assert 200 in get_method["response_codes"] or "200" in get_method["response_codes"]

        elif report_format == "csv":
            # CSV has 1 SWAGGER row + 4 methods + 1 TOTAL row = 6 rows
            assert len(content) == 6
            # Find GET method row (first row of /get path has Path filled)
            get_row = next(r for r in content if r["Method"] == "GET" and r["Path"] == "/get")
            assert get_row["Method Count"] == "4"
            assert get_row["Covered"] == "Yes"

            # Check uncovered methods
            put_row = next(r for r in content if r["Method"] == "PUT")
            assert put_row["Covered"] == "No"

        elif report_format == "html":
            assert "<!DOCTYPE html>" in content
            assert "API Coverage Report" in content
            assert "50.0%" in content or "50%" in content
            # Check 3-color scheme classes are present
            assert "covered" in content
            assert "not-covered" in content

    def test_100_percent_coverage(self, mock_api, collector_with_adapter, swagger_spec, output_dir):
        """Test generating report with 100% coverage.

        This test covers ALL endpoints to show what a fully covered API looks like.
        """
        collector = collector_with_adapter
        collector.set_current_test("test_100_percent_coverage")

        # Cover ALL endpoints
        requests.get("http://mock-api.local/get")
        requests.post("http://mock-api.local/post", json={"data": "test"})
        requests.put("http://mock-api.local/put", json={"data": "update"})
        requests.delete("http://mock-api.local/delete")

        # Generate report
        reporter = CoverageReporter(swagger_spec)
        reporter.process_interactions(collector.get_data())
        report_data = reporter.generate_report()

        # Write all formats
        JsonWriter.write(report_data, output_dir / "full_coverage.json")
        CsvWriter.write(report_data, output_dir / "full_coverage.csv")
        HtmlWriter.write(report_data, output_dir / "full_coverage.html")

        # Verify 100% coverage
        assert report_data["summary"]["coverage_percentage"] == 100.0
        assert report_data["summary"]["covered_endpoints"] == 4
        assert report_data["summary"]["total_endpoints"] == 4

        # All paths and methods should be covered
        for path_entry in report_data["endpoints"]:
            assert path_entry["is_covered"], f"Path {path_entry['path']} not covered"
            for method in path_entry["methods"]:
                assert method["is_covered"], f"Method {method['method']} on {path_entry['path']} not covered"

    def test_zero_coverage(self, swagger_spec, output_dir, make_coverage_report):
        """Test generating report with 0% coverage.

        This test makes NO requests to show what an uncovered API looks like.
        """
        # Generate report with no interactions
        report_data = make_coverage_report(swagger_spec, [])

        # Write all formats
        JsonWriter.write(report_data, output_dir / "zero_coverage.json")
        CsvWriter.write(report_data, output_dir / "zero_coverage.csv")
        HtmlWriter.write(report_data, output_dir / "zero_coverage.html")

        # Verify 0% coverage
        assert report_data["summary"]["coverage_percentage"] == 0.0
        assert report_data["summary"]["covered_endpoints"] == 0
        assert report_data["summary"]["total_endpoints"] == 4
        assert report_data["summary"]["total_requests"] == 0

        # All paths and methods should be uncovered
        for path_entry in report_data["endpoints"]:
            assert not path_entry["is_covered"], f"Path {path_entry['path']} should not be covered"
            for method in path_entry["methods"]:
                path = path_entry["path"]
                assert not method["is_covered"], f"Method {method['method']} on {path} should not be covered"


# ============================================================================
# Report Format Verification Tests
# ============================================================================


class TestReportFormats:
    """Verify specific report format details."""

    @pytest.fixture
    def sample_report_data(self, mock_api, collector_with_adapter, swagger_spec):
        """Generate sample report data with mixed coverage."""
        collector = collector_with_adapter
        collector.set_current_test("sample_test")

        # Make varied requests
        requests.get("http://mock-api.local/get")
        requests.get("http://mock-api.local/get")
        requests.post("http://mock-api.local/post", json={"x": 1})

        reporter = CoverageReporter(swagger_spec)
        reporter.process_interactions(collector.get_data())
        return reporter.generate_report()

    def test_json_report_structure(self, sample_report_data, output_dir):
        """Verify JSON report has correct structure."""
        output_path = output_dir / "structure_test.json"
        JsonWriter.write(sample_report_data, output_path)

        data = json.loads(output_path.read_text())

        # Check top-level keys
        assert "format_version" in data
        assert "generated_at" in data
        assert "summary" in data
        assert "endpoints" in data

        # Check summary structure
        summary = data["summary"]
        assert "total_endpoints" in summary
        assert "covered_endpoints" in summary
        assert "coverage_percentage" in summary
        assert "total_requests" in summary

        # Check endpoint structure (grouped by path)
        for path_entry in data["endpoints"]:
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

    def test_csv_report_structure(self, sample_report_data, output_dir):
        """Verify CSV report has correct columns (grouped format)."""
        output_path = output_dir / "structure_test.csv"
        CsvWriter.write(sample_report_data, output_path)

        with open(output_path, newline="") as f:
            reader = csv.reader(f)
            headers = next(reader)

        expected_headers = ["Path", "Hit Count", "Method", "Method Count", "Response Codes", "Covered"]
        assert headers == expected_headers

    def test_html_report_contains_all_sections(self, sample_report_data, output_dir):
        """Verify HTML report contains all required sections."""
        output_path = output_dir / "structure_test.html"
        HtmlWriter.write(sample_report_data, output_path)

        content = output_path.read_text()

        # Check HTML structure
        assert "<!DOCTYPE html>" in content
        assert "<title>API Coverage Report</title>" in content

        # Check summary section
        assert "Coverage" in content
        assert "Endpoints Covered" in content
        assert "Total Requests" in content

        # Check table headers (grouped format: Path first, then Method)
        # Some headers are sortable (have class="sortable")
        assert ">Path</th>" in content
        assert ">Hit Count</th>" in content
        assert "<th>Method</th>" in content
        assert "<th>Method Count</th>" in content
        assert "<th>Response Codes</th>" in content
        assert ">Status</th>" in content

        # Check CSS classes for 3-color scheme (C8)
        assert ".badge-success" in content  # Green: hit_count > 1
        assert ".badge-warning" in content  # Gray: hit_count == 1
        assert ".badge-danger" in content  # Red: not covered


# ============================================================================
# Grouped Report Format Tests
# ============================================================================


class TestGroupedReportFormat:
    """Tests for verifying the new grouped-by-path report format."""

    @pytest.fixture
    def multi_method_swagger_spec(self, make_swagger_spec):
        """Swagger spec with 2 paths, each having multiple methods."""
        return make_swagger_spec(
            endpoints=[
                # /users path with GET, POST, PUT methods
                ("GET", "/users"),
                ("POST", "/users"),
                ("PUT", "/users"),
                # /orders path with GET, POST, DELETE methods
                ("GET", "/orders"),
                ("POST", "/orders"),
                ("DELETE", "/orders"),
            ],
            base_path="/api",
            title="Multi-Method API",
        )

    @pytest.fixture
    def multi_method_mock_api(self):
        """Setup mock API with multiple status codes per method."""
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            # /users endpoints - multiple response codes
            # GET /users - 200, 200, 404, 500
            rsps.add(responses.GET, "http://test-api.local/api/users", status=200)
            rsps.add(responses.GET, "http://test-api.local/api/users", status=200)
            rsps.add(responses.GET, "http://test-api.local/api/users", status=404)
            rsps.add(responses.GET, "http://test-api.local/api/users", status=500)
            # POST /users - 201, 201, 400
            rsps.add(responses.POST, "http://test-api.local/api/users", status=201)
            rsps.add(responses.POST, "http://test-api.local/api/users", status=201)
            rsps.add(responses.POST, "http://test-api.local/api/users", status=400)
            # PUT /users - 200, 404
            rsps.add(responses.PUT, "http://test-api.local/api/users", status=200)
            rsps.add(responses.PUT, "http://test-api.local/api/users", status=404)

            # /orders endpoints - multiple response codes
            # GET /orders - 200, 200, 200
            rsps.add(responses.GET, "http://test-api.local/api/orders", status=200)
            rsps.add(responses.GET, "http://test-api.local/api/orders", status=200)
            rsps.add(responses.GET, "http://test-api.local/api/orders", status=200)
            # POST /orders - 201, 400, 422
            rsps.add(responses.POST, "http://test-api.local/api/orders", status=201)
            rsps.add(responses.POST, "http://test-api.local/api/orders", status=400)
            rsps.add(responses.POST, "http://test-api.local/api/orders", status=422)
            # DELETE /orders - 204, 204, 404
            rsps.add(responses.DELETE, "http://test-api.local/api/orders", status=204)
            rsps.add(responses.DELETE, "http://test-api.local/api/orders", status=204)
            rsps.add(responses.DELETE, "http://test-api.local/api/orders", status=404)

            yield rsps

    def test_grouped_report_multiple_methods_and_status_codes(
        self,
        multi_method_mock_api,
        collector_with_adapter,
        multi_method_swagger_spec,
        output_dir,
    ):
        """Test grouped report format with multiple methods per path and various status codes.

        This test verifies:
        1. Endpoints are grouped by path (2 paths: /users, /orders)
        2. Each path shows total hit count across all methods
        3. Methods within path show individual hit counts
        4. Response codes are tracked per method with counts
        5. Reports are generated in all formats (JSON, CSV, HTML)
        """
        collector = collector_with_adapter
        collector.set_current_test("test_grouped_report_multiple_methods_and_status_codes")

        # Make requests to /users path (3 methods, various status codes)
        # GET /users - 4 requests: 200, 200, 404, 500
        requests.get("http://test-api.local/api/users")
        requests.get("http://test-api.local/api/users")
        requests.get("http://test-api.local/api/users")
        requests.get("http://test-api.local/api/users")

        # POST /users - 3 requests: 201, 201, 400
        requests.post("http://test-api.local/api/users", json={"name": "Alice"})
        requests.post("http://test-api.local/api/users", json={"name": "Bob"})
        requests.post("http://test-api.local/api/users", json={})  # 400

        # PUT /users - 2 requests: 200, 404
        requests.put("http://test-api.local/api/users", json={"name": "Updated"})
        requests.put("http://test-api.local/api/users", json={"id": 999})  # 404

        # Make requests to /orders path (3 methods, various status codes)
        # GET /orders - 3 requests: 200, 200, 200
        requests.get("http://test-api.local/api/orders")
        requests.get("http://test-api.local/api/orders")
        requests.get("http://test-api.local/api/orders")

        # POST /orders - 3 requests: 201, 400, 422
        requests.post("http://test-api.local/api/orders", json={"item": "Widget"})
        requests.post("http://test-api.local/api/orders", json={})  # 400
        requests.post("http://test-api.local/api/orders", json={"invalid": True})  # 422

        # DELETE /orders - 3 requests: 204, 204, 404
        requests.delete("http://test-api.local/api/orders")
        requests.delete("http://test-api.local/api/orders")
        requests.delete("http://test-api.local/api/orders")  # 404

        # Generate report
        reporter = CoverageReporter(multi_method_swagger_spec)
        reporter.process_interactions(collector.get_data())
        report_data = reporter.generate_report()

        # Write reports in all formats
        json_path = output_dir / "grouped_coverage.json"
        csv_path = output_dir / "grouped_coverage.csv"
        html_path = output_dir / "grouped_coverage.html"

        JsonWriter.write(report_data, json_path)
        CsvWriter.write(report_data, csv_path)
        HtmlWriter.write(report_data, html_path)

        # Verify all files created
        assert json_path.exists()
        assert csv_path.exists()
        assert html_path.exists()

        # ===== Verify JSON report structure =====
        json_data = json.loads(json_path.read_text())

        # Summary: 6 endpoints total, all covered, 18 total requests
        assert json_data["summary"]["total_endpoints"] == 6
        assert json_data["summary"]["covered_endpoints"] == 6
        assert json_data["summary"]["coverage_percentage"] == 100.0
        assert json_data["summary"]["total_requests"] == 18

        # Should have 2 grouped paths
        assert len(json_data["endpoints"]) == 2

        # Find /users path (9 total hits: 4 GET + 3 POST + 2 PUT)
        users_path = next(e for e in json_data["endpoints"] if e["path"] == "/users")
        assert users_path["hit_count"] == 9
        assert users_path["is_covered"] is True
        assert users_path["all_methods_covered"] is True
        assert len(users_path["methods"]) == 3

        # Verify /users methods (sorted alphabetically: GET, POST, PUT)
        # Note: JSON serializes integer keys as strings
        users_get = next(m for m in users_path["methods"] if m["method"] == "GET")
        assert users_get["hit_count"] == 4
        assert users_get["response_codes"] == {"200": 2, "404": 1, "500": 1}

        users_post = next(m for m in users_path["methods"] if m["method"] == "POST")
        assert users_post["hit_count"] == 3
        assert users_post["response_codes"] == {"201": 2, "400": 1}

        users_put = next(m for m in users_path["methods"] if m["method"] == "PUT")
        assert users_put["hit_count"] == 2
        assert users_put["response_codes"] == {"200": 1, "404": 1}

        # Find /orders path (9 total hits: 3 GET + 3 POST + 3 DELETE)
        orders_path = next(e for e in json_data["endpoints"] if e["path"] == "/orders")
        assert orders_path["hit_count"] == 9
        assert orders_path["is_covered"] is True
        assert orders_path["all_methods_covered"] is True
        assert len(orders_path["methods"]) == 3

        # Verify /orders methods (sorted alphabetically: DELETE, GET, POST)
        orders_delete = next(m for m in orders_path["methods"] if m["method"] == "DELETE")
        assert orders_delete["hit_count"] == 3
        assert orders_delete["response_codes"] == {"204": 2, "404": 1}

        orders_get = next(m for m in orders_path["methods"] if m["method"] == "GET")
        assert orders_get["hit_count"] == 3
        assert orders_get["response_codes"] == {"200": 3}

        orders_post = next(m for m in orders_path["methods"] if m["method"] == "POST")
        assert orders_post["hit_count"] == 3
        assert orders_post["response_codes"] == {"201": 1, "400": 1, "422": 1}

        # ===== Verify CSV report structure =====
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            csv_rows = list(reader)

        # 6 method rows + 1 TOTAL row = 7 rows
        assert len(csv_rows) == 7

        # Find /users GET row (first row of /users path has Path filled)
        users_get_row = next(r for r in csv_rows if r["Method"] == "GET" and r["Path"] == "/users")
        assert users_get_row["Hit Count"] == "9"  # Total for path
        assert users_get_row["Method Count"] == "4"  # Method-specific
        assert "200(2)" in users_get_row["Response Codes"]
        assert "404(1)" in users_get_row["Response Codes"]
        assert "500(1)" in users_get_row["Response Codes"]

        # ===== Verify HTML report structure =====
        html_content = html_path.read_text()

        # Check paths are present
        assert "/users" in html_content
        assert "/orders" in html_content

        # Check all methods are present
        assert "GET" in html_content
        assert "POST" in html_content
        assert "PUT" in html_content
        assert "DELETE" in html_content

        # Check response codes are displayed
        assert "200" in html_content
        assert "201" in html_content
        assert "204" in html_content
        assert "400" in html_content
        assert "404" in html_content
        assert "422" in html_content
        assert "500" in html_content

        # Check rowspan is used for grouping (Path cell spans multiple rows)
        assert 'rowspan="3"' in html_content  # Both paths have 3 methods

        # Check coverage badges
        assert "badge-success" in html_content  # All methods have hit_count > 1
