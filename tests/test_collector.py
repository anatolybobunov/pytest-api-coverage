"""Tests for CoverageCollector."""

import threading
from concurrent.futures import ThreadPoolExecutor

from pytest_api_coverage.collector import CoverageCollector, HTTPInterceptor


def test_collector_implements_protocol():
    """Test that CoverageCollector implements HTTPInterceptor protocol."""
    collector = CoverageCollector()
    assert isinstance(collector, HTTPInterceptor)


def test_collector_record_and_get_data(make_interaction):
    """Test basic record and get_data operations."""
    collector = CoverageCollector()
    interaction = make_interaction()

    collector.record(interaction)
    data = collector.get_data()

    assert len(data) == 1
    assert data[0]["request"]["method"] == "GET"
    assert data[0]["request"]["path"] == "/users"
    assert data[0]["response"]["status_code"] == 200


def test_collector_set_current_test(make_interaction):
    """Test that current test name is attributed to interactions."""
    collector = CoverageCollector()
    collector.set_current_test("test_example")

    interaction = make_interaction(path="/")

    collector.record(interaction)
    data = collector.get_data()

    assert data[0]["test_name"] == "test_example"


def test_collector_test_name_in_interaction_takes_precedence(make_interaction):
    """Test that test_name in interaction overrides current test."""
    collector = CoverageCollector()
    collector.set_current_test("current_test")

    interaction = make_interaction(path="/", test_name="explicit_test")

    collector.record(interaction)
    data = collector.get_data()

    # Explicit test_name takes precedence
    assert data[0]["test_name"] == "explicit_test"


def test_collector_has_data(make_interaction):
    """Test has_data method."""
    collector = CoverageCollector()
    assert collector.has_data() is False

    collector.record(make_interaction(path="/"))

    assert collector.has_data() is True


def test_collector_clear(make_interaction):
    """Test clear method."""
    collector = CoverageCollector()

    collector.record(make_interaction(path="/"))

    assert collector.has_data() is True
    collector.clear()
    assert collector.has_data() is False


def test_collector_thread_safety(make_interaction):
    """Test that collector is thread-safe."""
    collector = CoverageCollector()
    num_threads = 10
    records_per_thread = 100

    def record_interactions(thread_id: int) -> None:
        for i in range(records_per_thread):
            interaction = make_interaction(path=f"/t{thread_id}/{i}")
            collector.record(interaction)

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        executor.map(record_interactions, range(num_threads))

    data = collector.get_data()
    assert len(data) == num_threads * records_per_thread


def test_collector_concurrent_set_test_and_record(make_interaction):
    """Test concurrent set_current_test and record operations."""
    collector = CoverageCollector()
    results = []
    lock = threading.Lock()

    def worker(test_name: str) -> None:
        collector.set_current_test(test_name)
        interaction = make_interaction(path="/")
        collector.record(interaction)
        data = collector.get_data()
        with lock:
            results.append(len(data))

    threads = [threading.Thread(target=worker, args=(f"test_{i}",)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All records should be captured
    assert collector.has_data()


def test_collector_interaction_to_dict(make_interaction):
    """Test that interaction is properly serialized to dict."""
    collector = CoverageCollector()

    interaction = make_interaction(
        method="POST",
        path="/users",
        status_code=201,
        headers={"Content-Type": "application/json"},
        query_params={"page": ["1"]},
        body={"name": "test"},
        response_headers={"X-Request-Id": "abc123"},
        duration_ms=123.45,
    )

    collector.record(interaction)
    data = collector.get_data()[0]

    # Verify request fields
    assert data["request"]["method"] == "POST"
    assert data["request"]["url"] == "http://test.com/users"
    assert data["request"]["path"] == "/users"
    assert data["request"]["host"] == "test.com"
    assert data["request"]["headers"] == {"Content-Type": "application/json"}
    assert data["request"]["query_params"] == {"page": ["1"]}
    assert data["request"]["body"] == {"name": "test"}

    # Verify response fields
    assert data["response"]["status_code"] == 201
    assert data["response"]["headers"] == {"X-Request-Id": "abc123"}

    # Verify metadata
    assert data["duration_ms"] == 123.45
    assert "timestamp" in data
