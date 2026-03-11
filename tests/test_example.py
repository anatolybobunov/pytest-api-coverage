"""Example test that generates coverage reports for demonstration.

Generates: example.html, example.json, example.csv in coverage-output/
"""

from __future__ import annotations

from pathlib import Path

import requests
import responses

from pytest_api_coverage.adapters.requests_adapter import RequestsAdapter
from pytest_api_coverage.collector import CoverageCollector
from pytest_api_coverage.reporter import CoverageReporter
from pytest_api_coverage.schemas import SwaggerParser
from pytest_api_coverage.writers import CsvWriter, HtmlWriter, JsonWriter

BASE_URL = "http://example-api.local"


def setup_mock_api(rsps: responses.RequestsMock) -> None:
    """Setup all mock endpoints."""
    # Users
    rsps.add(responses.GET, f"{BASE_URL}/users", json=[], status=200)
    rsps.add(responses.POST, f"{BASE_URL}/users", json={"id": 1}, status=201)
    rsps.add(responses.GET, f"{BASE_URL}/users/1", json={"id": 1, "name": "John"}, status=200)
    rsps.add(responses.GET, f"{BASE_URL}/users/999", json={"error": "not found"}, status=404)
    rsps.add(responses.PUT, f"{BASE_URL}/users/1", json={"id": 1}, status=200)
    rsps.add(responses.DELETE, f"{BASE_URL}/users/1", status=204)

    # Products
    rsps.add(responses.GET, f"{BASE_URL}/products", json=[], status=200)
    rsps.add(responses.POST, f"{BASE_URL}/products", json={"id": 1}, status=201)
    rsps.add(responses.GET, f"{BASE_URL}/products/1", json={"id": 1}, status=200)
    rsps.add(responses.PUT, f"{BASE_URL}/products/1", json={"id": 1}, status=200)
    rsps.add(responses.PATCH, f"{BASE_URL}/products/1", json={"id": 1}, status=200)
    rsps.add(responses.DELETE, f"{BASE_URL}/products/1", status=204)

    # Orders
    rsps.add(responses.GET, f"{BASE_URL}/orders", json=[], status=200)
    rsps.add(responses.POST, f"{BASE_URL}/orders", json={"id": 1}, status=201)
    rsps.add(responses.GET, f"{BASE_URL}/orders/1", json={"id": 1}, status=200)
    rsps.add(responses.PUT, f"{BASE_URL}/orders/1", json={"id": 1}, status=200)
    rsps.add(responses.DELETE, f"{BASE_URL}/orders/1", status=204)
    rsps.add(responses.GET, f"{BASE_URL}/orders/1/items", json=[], status=200)
    rsps.add(responses.POST, f"{BASE_URL}/orders/1/items", json={"id": 1}, status=201)

    # Categories
    rsps.add(responses.GET, f"{BASE_URL}/categories", json=[], status=200)
    rsps.add(responses.POST, f"{BASE_URL}/categories", json={"id": 1}, status=201)
    rsps.add(responses.GET, f"{BASE_URL}/categories/1", json={"id": 1}, status=200)
    rsps.add(responses.PUT, f"{BASE_URL}/categories/1", json={"id": 1}, status=200)
    rsps.add(responses.DELETE, f"{BASE_URL}/categories/1", status=204)

    # Auth
    rsps.add(responses.POST, f"{BASE_URL}/auth/login", json={"token": "abc"}, status=200)
    rsps.add(responses.POST, f"{BASE_URL}/auth/logout", json={}, status=200)
    rsps.add(responses.POST, f"{BASE_URL}/auth/refresh", json={"token": "xyz"}, status=200)

    # Health & Metrics
    rsps.add(responses.GET, f"{BASE_URL}/health", json={"status": "ok"}, status=200)
    rsps.add(responses.GET, f"{BASE_URL}/metrics", json={}, status=200)


@responses.activate
def test_generate_example_reports():
    """Generate example coverage reports demonstrating partial coverage."""
    setup_mock_api(responses)

    # Setup collector
    collector = CoverageCollector()
    adapter = RequestsAdapter(collector)
    adapter.install()
    collector.set_current_test("test_generate_example_reports")

    try:
        # === Make requests (partial coverage) ===

        # Users - cover all methods with different response codes
        requests.get(f"{BASE_URL}/users")
        requests.get(f"{BASE_URL}/users")  # duplicate call
        requests.post(f"{BASE_URL}/users", json={"name": "Alice"})
        requests.get(f"{BASE_URL}/users/1")
        requests.get(f"{BASE_URL}/users/999")  # 404 response
        requests.put(f"{BASE_URL}/users/1", json={"name": "Alice Updated"})
        # Skip DELETE /users/{id} - uncovered

        # Products - partial coverage
        requests.get(f"{BASE_URL}/products")
        requests.get(f"{BASE_URL}/products/1")
        requests.patch(f"{BASE_URL}/products/1", json={"price": 99})
        # Skip POST, PUT, DELETE - uncovered

        # Orders - minimal coverage
        requests.get(f"{BASE_URL}/orders")
        requests.post(f"{BASE_URL}/orders", json={"items": []})
        # Skip other order endpoints - uncovered

        # Categories - no coverage (all uncovered)

        # Auth - cover login only
        requests.post(f"{BASE_URL}/auth/login", json={"user": "test", "pass": "test"})
        # Skip logout and refresh - uncovered

        # Health & Metrics - full coverage
        requests.get(f"{BASE_URL}/health")
        requests.get(f"{BASE_URL}/metrics")

    finally:
        adapter.uninstall()

    # Load swagger spec
    swagger_path = Path(__file__).parent / "test_data" / "swagger_example.json"
    swagger_spec = SwaggerParser.parse(swagger_path)

    # Generate report
    reporter = CoverageReporter(swagger_spec)
    reporter.process_interactions(collector.get_data())
    report_data = reporter.generate_report()

    # Output directory
    output_dir = Path(__file__).parent.parent / "coverage-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write all formats
    HtmlWriter.write(report_data, output_dir / "example.html")
    JsonWriter.write(report_data, output_dir / "example.json")
    CsvWriter.write(report_data, output_dir / "example.csv")

    # Verify files created
    assert (output_dir / "example.html").exists()
    assert (output_dir / "example.json").exists()
    assert (output_dir / "example.csv").exists()

    # Verify partial coverage (not 0%, not 100%)
    summary = report_data["summary"]
    assert 0 < summary["coverage_percentage"] < 100
    assert summary["total_endpoints"] == 28
    assert summary["covered_endpoints"] > 0
    assert summary["covered_endpoints"] < summary["total_endpoints"]
