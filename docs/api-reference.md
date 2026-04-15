# API Reference

All public symbols are importable directly from `pytest_api_coverage`. These classes are useful for programmatic access to coverage data, custom reporting, or extending the plugin.

```python
from pytest_api_coverage import (
    CoverageCollector,
    HTTPInterceptor,
    HTTPInteraction,
    HTTPRequest,
    HTTPResponse,
    EndpointCoverage,
    MethodCoverage,
    PathCoverage,
)
```

---

## Data Models

### HTTPRequest

Immutable (`frozen=True`) representation of an HTTP request.

| Field | Type | Description |
|---|---|---|
| `method` | `str` | HTTP method (e.g. `"GET"`, `"POST"`). |
| `url` | `str` | Full URL including scheme, host, path, and query string. |
| `path` | `str` | URL path component only (e.g. `"/api/users/1"`). |
| `host` | `str` | Hostname extracted from the URL. |
| `headers` | `dict[str, str]` | Request headers. Defaults to an empty dict. |
| `query_params` | `dict[str, Any]` | Parsed query parameters. Defaults to an empty dict. |
| `body` | `Any \| None` | Request body. `None` if not present. |
| `content_type` | `str \| None` | Value of the `Content-Type` header. `None` if absent. |

---

### HTTPResponse

Immutable (`frozen=True`) representation of an HTTP response.

| Field | Type | Description |
|---|---|---|
| `status_code` | `int` | HTTP status code (e.g. `200`, `404`). |
| `headers` | `dict[str, str]` | Response headers. Defaults to an empty dict. |
| `content_type` | `str \| None` | Value of the `Content-Type` response header. `None` if absent. |
| `body_size` | `int` | Size of the response body in bytes. Defaults to `0`. |

---

### HTTPInteraction

A complete HTTP request-response pair. Mutable because `test_name` may be assigned after creation once the collector resolves the active test context.

| Field | Type | Description |
|---|---|---|
| `request` | `HTTPRequest` | The outgoing request. |
| `response` | `HTTPResponse` | The received response. |
| `timestamp` | `datetime` | UTC timestamp when the interaction was recorded. Defaults to `datetime.now(UTC)`. |
| `duration_ms` | `float` | Round-trip duration in milliseconds. Defaults to `0.0`. |
| `test_name` | `str \| None` | Name of the test that triggered this interaction. `None` if attribution could not be determined. |

---

### EndpointCoverage

Coverage data for a single API endpoint, identified by both method and path.

| Field | Type | Description |
|---|---|---|
| `method` | `str` | HTTP method (e.g. `"GET"`). |
| `path` | `str` | URL path (e.g. `"/api/users"`). |
| `hit_count` | `int` | Number of times this endpoint was called. Defaults to `0`. |
| `response_codes` | `dict[int, int]` | Map of status code to call count (e.g. `{200: 3, 404: 1}`). Defaults to an empty dict. |
| `test_names` | `set[str]` | Names of tests that hit this endpoint. Defaults to an empty set. |

**Properties:**

| Property | Type | Description |
|---|---|---|
| `is_covered` | `bool` | `True` if `hit_count > 0`. |

**Methods:**

| Method | Signature | Description |
|---|---|---|
| `record_hit` | `(status_code: int, test_name: str \| None = None) -> None` | Increments `hit_count`, updates `response_codes`, and records `test_name` if provided. |
| `to_dict` | `() -> dict[str, Any]` | Returns a serializable dict suitable for report output. |

---

### MethodCoverage

Coverage data for a single HTTP method on an API path. Used as an element within `PathCoverage.methods`.

| Field | Type | Description |
|---|---|---|
| `method` | `str` | HTTP method (e.g. `"DELETE"`). |
| `hit_count` | `int` | Number of times this method was called on the parent path. Defaults to `0`. |
| `response_codes` | `dict[int, int]` | Map of status code to call count. Defaults to an empty dict. |
| `test_names` | `set[str]` | Names of tests that triggered this method. Defaults to an empty set. |

**Properties:**

| Property | Type | Description |
|---|---|---|
| `is_covered` | `bool` | `True` if `hit_count > 0`. |

**Methods:**

| Method | Signature | Description |
|---|---|---|
| `to_dict` | `() -> dict[str, Any]` | Returns a serializable dict suitable for report output. |

---

### PathCoverage

Coverage data for a URL path, grouping all HTTP methods observed on that path.

| Field | Type | Description |
|---|---|---|
| `path` | `str` | URL path (e.g. `"/api/orders"`). |
| `methods` | `list[MethodCoverage]` | Coverage records for each method observed on this path. Defaults to an empty list. |

**Properties:**

| Property | Type | Description |
|---|---|---|
| `total_hit_count` | `int` | Sum of `hit_count` across all entries in `methods`. |
| `is_covered` | `bool` | `True` if any method in `methods` has been hit. |
| `all_methods_covered` | `bool` | `True` if every method in `methods` has been hit at least once. |

**Methods:**

| Method | Signature | Description |
|---|---|---|
| `to_dict` | `() -> dict[str, Any]` | Returns a serializable dict suitable for report output. |

---

## Core Classes

### CoverageCollector

Thread-safe collector for HTTP coverage data. This is the central object that the plugin creates and uses to accumulate `HTTPInteraction` records during a test session.

The implementation uses a `Queue` for lock-free writes from multiple threads. A `Lock` is held during queue drain and data access to ensure consistency. It works correctly in single-threaded pytest, multi-threaded test execution, and pytest-xdist worker processes.

**Constructor:**

```python
collector = CoverageCollector()
```

Takes no arguments.

**Public methods:**

| Method | Signature | Description |
|---|---|---|
| `set_current_test` | `(test_name: str \| None) -> None` | Stores the active test name in a `ContextVar` for automatic attribution. Called by the plugin's pytest hooks. |
| `record` | `(interaction: HTTPInteraction) -> None` | Records an `HTTPInteraction`. If `interaction.test_name` is `None`, the current test name from the `ContextVar` is applied before queuing. |
| `has_data` | `() -> bool` | Returns `True` if at least one interaction has been recorded. |
| `get_data` | `() -> list[dict[str, Any]]` | Drains the internal queue into the data buffer and returns all collected interactions as serializable dicts. The data buffer is not cleared — call `clear()` to reset it. |
| `clear` | `() -> None` | Drains the queue and discards all collected data. |
| `record_error` | `() -> None` | Increments the internal error counter. Called when an interceptor fails to record an interaction. |

**Properties:**

| Property | Type | Description |
|---|---|---|
| `record_error_count` | `int` | Number of recording errors accumulated so far. |

---

### HTTPInterceptor

A `Protocol` (structural interface) for objects that can receive and record `HTTPInteraction` instances. Any object implementing a `record` method with the correct signature satisfies this protocol at runtime (`@runtime_checkable`).

The plugin ships adapters that implement this protocol for `httpx` and `requests`. You can implement your own adapter for other HTTP libraries by satisfying this interface.

**Protocol method:**

| Method | Signature | Description |
|---|---|---|
| `record` | `(interaction: HTTPInteraction) -> None` | Accepts a completed `HTTPInteraction` and stores or forwards it. |

**Checking conformance at runtime:**

```python
from pytest_api_coverage import HTTPInterceptor

assert isinstance(my_adapter, HTTPInterceptor)
```

**Example — recording a custom interaction:**

```python
from pytest_api_coverage.models import HTTPRequest, HTTPResponse, HTTPInteraction
from pytest_api_coverage.collector import CoverageCollector

collector = CoverageCollector()

# Build request and response objects.
# HTTPRequest requires method, url, path, and host.
request = HTTPRequest(
    method="GET",
    url="https://api.example.com/users",
    path="/users",
    host="api.example.com",
    headers={"Authorization": "Bearer token"},
)
response = HTTPResponse(status_code=200, headers={"Content-Type": "application/json"})

# Create the interaction. test_name is optional — if omitted,
# the collector fills it from the current test context automatically.
interaction = HTTPInteraction(
    request=request,
    response=response,
    test_name="test_get_users",
)

collector.record(interaction)

# Retrieve recorded data as serializable dicts.
data = collector.get_data()
```

If you need to build a custom report from the structured model types rather than raw dicts, use `get_data()` to retrieve the serialized interactions and reconstruct them, or access `_data` directly (internal, unsupported) after calling `_drain_queue()`.

---

## See Also

- [Architecture](architecture.md) — how these components fit together internally
- [Configuration](configuration.md) — pytest options and environment variables
- [Usage](usage.md) — getting started and common patterns
- [Reports](reports.md) — understanding the output formats
