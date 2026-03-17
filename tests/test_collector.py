"""Tests for CoverageCollector."""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from enum import Enum

import pytest

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


def _assert_execnet_serializable(obj: object) -> None:
    """Recursively assert that obj contains only execnet-serializable basic types."""
    allowed = (str, int, float, bool, bytes, type(None))
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert isinstance(k, (str, int)), f"dict key {k!r} is not serializable (type {type(k)})"
            _assert_execnet_serializable(v)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _assert_execnet_serializable(item)
    else:
        assert isinstance(obj, allowed), f"value {obj!r} is not serializable (type {type(obj)})"


def test_get_data_serializable_with_decimal_body(make_interaction):
    """get_data() must return execnet-serializable dicts even when body contains Decimal."""
    collector = CoverageCollector()
    interaction = make_interaction(
        method="POST",
        path="/orders",
        body={"price": Decimal("19.99"), "quantity": Decimal("3")},
    )
    collector.record(interaction)

    data = collector.get_data()

    _assert_execnet_serializable(data)


def test_get_data_serializable_with_enum_body(make_interaction):
    """get_data() must return execnet-serializable dicts even when body contains enums."""

    class TokenResponseFormat(Enum):
        JSON = "json"
        BINARY = "binary"

    collector = CoverageCollector()
    interaction = make_interaction(
        method="POST",
        path="/tokens",
        body={"format": TokenResponseFormat.JSON, "name": "my-token"},
    )
    collector.record(interaction)

    data = collector.get_data()

    _assert_execnet_serializable(data)


def test_get_data_serializable_with_decimal_query_params(make_interaction):
    """get_data() must return execnet-serializable dicts even when query_params contain Decimal."""
    collector = CoverageCollector()
    interaction = make_interaction(
        method="GET",
        path="/prices",
        query_params={"min_price": Decimal("5.00"), "max_price": Decimal("100.00")},
    )
    collector.record(interaction)

    data = collector.get_data()

    _assert_execnet_serializable(data)


@pytest.mark.asyncio
async def test_async_context_var_attribution_per_coroutine(make_interaction):
    """ContextVar gives each coroutine its own current-test attribution.

    Two coroutines run concurrently via asyncio.gather.  Each sets a
    different test name and records one interaction.  The ContextVar
    must keep the values isolated so neither coroutine overwrites the
    other's attribution.
    """
    collector = CoverageCollector()

    async def run_test(test_name: str, path: str) -> None:
        collector.set_current_test(test_name)
        # Yield to the event loop so both coroutines are interleaved.
        await asyncio.sleep(0)
        interaction = make_interaction(path=path)
        collector.record(interaction)

    await asyncio.gather(
        run_test("test_alpha", "/alpha"),
        run_test("test_beta", "/beta"),
    )

    data = collector.get_data()
    assert len(data) == 2

    by_path = {d["request"]["path"]: d["test_name"] for d in data}
    assert by_path["/alpha"] == "test_alpha"
    assert by_path["/beta"] == "test_beta"
