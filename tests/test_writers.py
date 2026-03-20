"""Tests for report writers."""

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pytest_api_coverage.writers import CsvWriter, HtmlWriter, JsonWriter


@pytest.fixture
def sample_report():
    """Create a sample report for testing writers (grouped by path)."""
    return {
        "format_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "split_by_origin": False,
        "summary": {
            "total_endpoints": 4,
            "covered_endpoints": 2,
            "coverage_percentage": 50.0,
            "total_requests": 5,
        },
        "endpoints": [
            {
                "path": "/users",
                "hit_count": 5,  # total: 3 + 2
                "is_covered": True,
                "all_methods_covered": True,
                "methods": [
                    {
                        "method": "GET",
                        "hit_count": 3,
                        "is_covered": True,
                        "response_codes": {200: 2, 404: 1},
                        "test_names": ["test_list", "test_search"],
                    },
                    {
                        "method": "POST",
                        "hit_count": 2,
                        "is_covered": True,
                        "response_codes": {201: 2},
                        "test_names": ["test_create"],
                    },
                ],
            },
            {
                "path": "/users/{id}",
                "hit_count": 0,
                "is_covered": False,
                "all_methods_covered": False,
                "methods": [
                    {
                        "method": "DELETE",
                        "hit_count": 0,
                        "is_covered": False,
                        "response_codes": {},
                        "test_names": [],
                    },
                    {
                        "method": "GET",
                        "hit_count": 0,
                        "is_covered": False,
                        "response_codes": {},
                        "test_names": [],
                    },
                ],
            },
        ],
    }


class TestJsonWriter:
    """Tests for JsonWriter."""

    def test_write_json(self, sample_report, tmp_path: Path):
        """Test writing JSON report."""
        output_path = tmp_path / "coverage.json"
        result = JsonWriter.write(sample_report, output_path)

        assert result == output_path
        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert data["summary"]["total_endpoints"] == 4
        # 2 grouped paths (each with methods inside)
        assert len(data["endpoints"]) == 2

    def test_json_format_version(self, sample_report, tmp_path: Path):
        """Test JSON includes format version."""
        output_path = tmp_path / "coverage.json"
        JsonWriter.write(sample_report, output_path)

        with open(output_path) as f:
            data = json.load(f)

        assert "format_version" in data
        assert data["format_version"] == "1.0"

    def test_json_indentation(self, sample_report, tmp_path: Path):
        """Test JSON is properly indented."""
        output_path = tmp_path / "coverage.json"
        JsonWriter.write(sample_report, output_path)

        content = output_path.read_text()
        # Should have newlines (not compact JSON)
        assert "\n" in content


class TestCsvWriter:
    """Tests for CsvWriter."""

    def test_write_csv(self, sample_report, tmp_path: Path):
        """Test writing CSV report."""
        output_path = tmp_path / "coverage.csv"
        result = CsvWriter.write(sample_report, output_path)

        assert result == output_path
        assert output_path.exists()

        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # 4 endpoints + 1 TOTAL row
        assert len(rows) == 5

    def test_csv_headers(self, sample_report, tmp_path: Path):
        """Test CSV has correct headers (grouped format)."""
        output_path = tmp_path / "coverage.csv"
        CsvWriter.write(sample_report, output_path)

        with open(output_path, newline="") as f:
            reader = csv.reader(f)
            headers = next(reader)

        expected = ["Path", "Hit Count", "Method", "Method Count", "Response Codes", "Covered"]
        assert headers == expected

    def test_csv_content(self, sample_report, tmp_path: Path):
        """Test CSV content is correct (grouped format)."""
        output_path = tmp_path / "coverage.csv"
        CsvWriter.write(sample_report, output_path)

        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Find GET method row under /users path
        # First row has Path="/users", subsequent rows have Path=""
        get_users = next(r for r in rows if r["Method"] == "GET" and r["Path"] == "/users")
        assert get_users["Hit Count"] == "5"  # Total for path
        assert get_users["Method Count"] == "3"  # Method-specific count
        assert get_users["Covered"] == "Yes"

        # Check TOTAL row (Path="TOTAL")
        total_row = next(r for r in rows if r["Path"] == "TOTAL")
        assert total_row["Covered"] == "50.0%"


class TestWriteReportsPrefix:
    """Tests for write_reports() optional prefix parameter (SET-02)."""

    def test_prefix_none_produces_standard_names(self, tmp_path, sample_report):
        from pytest_api_coverage.writers import write_reports

        files = write_reports(sample_report, tmp_path, {"json", "csv", "html"}, prefix=None)
        names = {f.name for f in files}
        assert "coverage.json" in names
        assert "coverage.csv" in names
        assert "coverage.html" in names

    def test_prefix_auth_produces_prefixed_names(self, tmp_path, sample_report):
        from pytest_api_coverage.writers import write_reports

        files = write_reports(sample_report, tmp_path, {"json", "csv", "html"}, prefix="auth")
        names = {f.name for f in files}
        assert "auth-coverage.json" in names
        assert "auth-coverage.csv" in names
        assert "auth-coverage.html" in names

    def test_prefix_orders_produces_prefixed_names(self, tmp_path, sample_report):
        from pytest_api_coverage.writers import write_reports

        files = write_reports(sample_report, tmp_path, {"json"}, prefix="orders")
        assert files[0].name == "orders-coverage.json"

    def test_no_prefix_kwarg_backward_compat(self, tmp_path, sample_report):
        from pytest_api_coverage.writers import write_reports

        # Positional-only call — must still work with no prefix arg
        files = write_reports(sample_report, tmp_path, {"json"})
        assert files[0].name == "coverage.json"


@pytest.fixture
def sample_split_report():
    """Sample split-by-origin report for testing writers."""
    return {
        "swagger_source": "api.yaml",
        "split_by_origin": True,
        "origins": {
            "https://api.example.com": {
                "summary": {
                    "total_endpoints": 4,
                    "covered_endpoints": 2,
                    "coverage_percentage": 50.0,
                    "total_requests": 2,
                },
                "endpoints": [
                    {
                        "path": "/users",
                        "hit_count": 2,
                        "is_covered": True,
                        "all_methods_covered": True,
                        "methods": [
                            {
                                "method": "GET",
                                "hit_count": 2,
                                "is_covered": True,
                                "response_codes": {200: 2},
                                "test_names": ["test_list"],
                            },
                        ],
                    },
                    {
                        "path": "/users/{id}",
                        "hit_count": 0,
                        "is_covered": False,
                        "all_methods_covered": False,
                        "methods": [
                            {
                                "method": "GET",
                                "hit_count": 0,
                                "is_covered": False,
                                "response_codes": {},
                                "test_names": [],
                            },
                        ],
                    },
                ],
            },
            "https://proxy.example.com": {
                "summary": {
                    "total_endpoints": 4,
                    "covered_endpoints": 1,
                    "coverage_percentage": 25.0,
                    "total_requests": 1,
                },
                "endpoints": [
                    {
                        "path": "/users",
                        "hit_count": 0,
                        "is_covered": False,
                        "all_methods_covered": False,
                        "methods": [
                            {
                                "method": "GET",
                                "hit_count": 0,
                                "is_covered": False,
                                "response_codes": {},
                                "test_names": [],
                            },
                        ],
                    },
                    {
                        "path": "/users/{id}",
                        "hit_count": 1,
                        "is_covered": True,
                        "all_methods_covered": True,
                        "methods": [
                            {
                                "method": "GET",
                                "hit_count": 1,
                                "is_covered": True,
                                "response_codes": {200: 1},
                                "test_names": ["test_get_user"],
                            },
                        ],
                    },
                ],
            },
        },
        "combined_summary": {
            "total_endpoints": 4,
            "covered_endpoints": 3,
            "coverage_percentage": 75.0,
            "total_requests": 3,
            "origins_count": 2,
        },
    }


class TestCsvWriterSplitMode:
    """Tests for CsvWriter._to_rows_split (split-by-origin mode)."""

    def test_split_csv_has_origin_column(self, sample_split_report, tmp_path: Path):
        """Split CSV includes Origin as the first column."""
        output_path = tmp_path / "split.csv"
        CsvWriter.write(sample_split_report, output_path)

        with open(output_path, newline="") as f:
            reader = csv.reader(f)
            headers = next(reader)

        assert headers[0] == "Origin"

    def test_split_csv_has_subtotal_rows_per_origin(self, sample_split_report, tmp_path: Path):
        """Split CSV has one SUBTOTAL row per origin."""
        output_path = tmp_path / "split.csv"
        CsvWriter.write(sample_split_report, output_path)

        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        subtotal_rows = [r for r in rows if r["Path"] == "SUBTOTAL"]
        assert len(subtotal_rows) == 2

    def test_split_csv_total_row_has_all_origin(self, sample_split_report, tmp_path: Path):
        """Split CSV TOTAL row has Origin='ALL'."""
        output_path = tmp_path / "split.csv"
        CsvWriter.write(sample_split_report, output_path)

        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        total_rows = [r for r in rows if r["Path"] == "TOTAL"]
        assert len(total_rows) == 1
        assert total_rows[0]["Origin"] == "ALL"

    def test_split_csv_subtotal_percentages(self, sample_split_report, tmp_path: Path):
        """SUBTOTAL rows show correct per-origin coverage percentages."""
        output_path = tmp_path / "split.csv"
        CsvWriter.write(sample_split_report, output_path)

        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        subtotals = {r["Origin"]: r for r in rows if r["Path"] == "SUBTOTAL"}
        assert subtotals["https://api.example.com"]["Covered"] == "50.0%"
        assert subtotals["https://proxy.example.com"]["Covered"] == "25.0%"

    def test_split_csv_total_combined_percentage(self, sample_split_report, tmp_path: Path):
        """TOTAL row shows combined_summary coverage percentage."""
        output_path = tmp_path / "split.csv"
        CsvWriter.write(sample_split_report, output_path)

        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        total_row = next(r for r in rows if r["Path"] == "TOTAL")
        assert total_row["Covered"] == "75.0%"

    def test_split_csv_endpoint_rows_have_origin(self, sample_split_report, tmp_path: Path):
        """Data rows (non-summary) include the origin they belong to."""
        output_path = tmp_path / "split.csv"
        CsvWriter.write(sample_split_report, output_path)

        with open(output_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        sentinel_origins = {"SWAGGER", "ALL"}
        data_rows = [r for r in rows if r["Origin"] not in sentinel_origins and r["Path"] not in ("SUBTOTAL", "")]
        for row in data_rows:
            assert row["Origin"] in {"https://api.example.com", "https://proxy.example.com"}


class TestHtmlWriterSplitMode:
    """Tests for HtmlWriter split-by-origin mode."""

    def test_split_html_mentions_split_by_origin(self, sample_split_report, tmp_path: Path):
        """Split HTML must say 'Split by Origin'."""
        output_path = tmp_path / "split.html"
        HtmlWriter.write(sample_split_report, output_path)

        assert "Split by Origin" in output_path.read_text()

    def test_split_html_has_per_origin_sections(self, sample_split_report, tmp_path: Path):
        """Split HTML contains a section for each origin."""
        output_path = tmp_path / "split.html"
        HtmlWriter.write(sample_split_report, output_path)

        content = output_path.read_text()
        assert "https://api.example.com" in content
        assert "https://proxy.example.com" in content

    def test_split_html_shows_combined_coverage(self, sample_split_report, tmp_path: Path):
        """Split HTML shows the combined coverage percentage."""
        output_path = tmp_path / "split.html"
        HtmlWriter.write(sample_split_report, output_path)

        assert "75.0%" in output_path.read_text()

    def test_split_html_origins_count(self, sample_split_report, tmp_path: Path):
        """Split HTML displays the number of origins from combined_summary."""
        output_path = tmp_path / "split.html"
        HtmlWriter.write(sample_split_report, output_path)

        content = output_path.read_text()
        # combined_summary.origins_count = 2; it appears in the Origins card
        assert "2" in content

    def test_split_html_is_valid_html(self, sample_split_report, tmp_path: Path):
        """Split HTML output starts with a proper DOCTYPE declaration."""
        output_path = tmp_path / "split.html"
        HtmlWriter.write(sample_split_report, output_path)

        assert output_path.read_text().startswith("<!DOCTYPE html>")

    def test_split_html_has_filter_bars(self, sample_split_report, tmp_path: Path):
        """Split HTML contains filter bars for each origin section."""
        output_path = tmp_path / "split.html"
        HtmlWriter.write(sample_split_report, output_path)
        content = output_path.read_text()
        assert "filter-bar" in content
        assert 'data-filter="covered"' in content
        assert 'data-filter="not-covered"' in content


class TestHtmlWriter:
    """Tests for HtmlWriter."""

    def test_write_html(self, sample_report, tmp_path: Path):
        """Test writing HTML report."""
        output_path = tmp_path / "coverage.html"
        result = HtmlWriter.write(sample_report, output_path)

        assert result == output_path
        assert output_path.exists()

        content = output_path.read_text()
        assert "<!DOCTYPE html>" in content

    def test_html_contains_title(self, sample_report, tmp_path: Path):
        """Test HTML contains title."""
        output_path = tmp_path / "coverage.html"
        HtmlWriter.write(sample_report, output_path)

        content = output_path.read_text()
        assert "API Coverage Report" in content

    def test_html_contains_summary(self, sample_report, tmp_path: Path):
        """Test HTML contains coverage summary."""
        output_path = tmp_path / "coverage.html"
        HtmlWriter.write(sample_report, output_path)

        content = output_path.read_text()
        assert "50.0%" in content or "50%" in content
        assert "2/4" in content or ("2" in content and "4" in content)

    def test_html_three_color_scheme(self, sample_report, tmp_path: Path):
        """Test HTML uses 3-color scheme: covered, partial-covered, not-covered."""
        output_path = tmp_path / "coverage.html"
        HtmlWriter.write(sample_report, output_path)

        content = output_path.read_text()
        assert "covered" in content
        assert "not-covered" in content
        assert "partial-covered" in content
        assert "covered-once" not in content

    def test_html_partial_covered_class(self, tmp_path: Path):
        """Test endpoint with mixed method coverage gets partial-covered class."""
        report = {
            "format_version": "1.0",
            "split_by_origin": False,
            "summary": {"total_endpoints": 1, "covered_endpoints": 0, "coverage_percentage": 0.0, "total_requests": 1},
            "endpoints": [
                {
                    "path": "/items",
                    "hit_count": 1,
                    "is_covered": True,
                    "all_methods_covered": False,
                    "methods": [
                        {"method": "GET", "hit_count": 2, "is_covered": True, "response_codes": {200: 2}, "test_names": []},
                        {"method": "POST", "hit_count": 0, "is_covered": False, "response_codes": {}, "test_names": []},
                    ],
                }
            ],
        }
        output_path = tmp_path / "partial.html"
        HtmlWriter.write(report, output_path)
        content = output_path.read_text()
        assert 'class="partial-covered"' in content

    def test_html_filter_bar_present(self, sample_report, tmp_path: Path):
        """Test HTML contains filter bar with buttons."""
        output_path = tmp_path / "coverage.html"
        HtmlWriter.write(sample_report, output_path)
        content = output_path.read_text()
        assert "filter-bar" in content
        assert 'data-filter="covered"' in content
        assert 'data-filter="partial-covered"' in content
        assert 'data-filter="not-covered"' in content

    def test_html_contains_endpoints(self, sample_report, tmp_path: Path):
        """Test HTML contains endpoint information."""
        output_path = tmp_path / "coverage.html"
        HtmlWriter.write(sample_report, output_path)

        content = output_path.read_text()
        assert "/users" in content
        assert "GET" in content
        assert "POST" in content
        assert "DELETE" in content

    def test_html_contains_response_codes(self, sample_report, tmp_path: Path):
        """Test HTML contains response codes."""
        output_path = tmp_path / "coverage.html"
        HtmlWriter.write(sample_report, output_path)

        content = output_path.read_text()
        # Response codes should be displayed
        assert "200" in content
        assert "201" in content
