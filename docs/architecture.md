# Architecture

## Overview

pytest-api-coverage is a pytest plugin that intercepts HTTP requests during test execution, matches them against an OpenAPI specification, and generates coverage reports.

> For detailed type signatures of the public classes described here, see the [API Reference](api-reference.md).

```
┌─────────────────────────────────────────────────────────────────┐
│                         pytest                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    plugin.py                            │    │
│  │  pytest_configure → pytest_sessionstart → pytest_runtest│    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                  │
│         ┌────────────────────┼────────────────────┐             │
│         ▼                    ▼                    ▼             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐        │
│  │  Adapters   │     │  Collector  │     │   Schemas   │        │
│  │  requests   │────▶│  thread-    │     │  swagger    │        │
│  │  httpx      │     │  safe       │     │  parser     │        │
│  └─────────────┘     └─────────────┘     └─────────────┘        │
│                              │                    │             │
│                              ▼                    ▼             │
│                       ┌─────────────────────────────┐           │
│                       │        Reporter             │           │
│                       │  path matching + coverage   │           │
│                       └─────────────────────────────┘           │
│                                     │                           │
│                    ┌────────────────┼────────────────┐          │
│                    ▼                ▼                ▼          │
│             ┌───────────┐    ┌───────────┐    ┌───────────┐     │
│             │   JSON    │    │    CSV    │    │   HTML    │     │
│             │  Writer   │    │  Writer   │    │  Writer   │     │
│             └───────────┘    └───────────┘    └───────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## Module Structure

```
src/pytest_api_coverage/
├── __init__.py
├── plugin.py           # Pytest plugin entry point
├── collector.py        # Thread-safe request collection
├── reporter.py         # Coverage matching and reporting
├── orchestrator.py     # MultiSpecOrchestrator — multi-spec routing
├── models.py           # Data models
├── terminal.py         # Terminal output (summary printing)
├── utils.py            # URL matching and normalization helpers
├── adapters/
│   ├── __init__.py
│   ├── base.py               # HttpAdapterProtocol interface
│   ├── requests_adapter.py   # requests library interception
│   └── httpx_adapter.py      # httpx library interception
├── config/
│   ├── __init__.py
│   ├── settings.py     # Configuration settings and SpecConfig
│   └── multi_spec.py   # Multi-spec config file loader
├── schemas/
│   ├── __init__.py
│   └── swagger.py      # OpenAPI parser
└── writers/
    ├── __init__.py
    ├── json_writer.py  # JSON report writer
    ├── csv_writer.py   # CSV report writer
    └── html_writer.py  # HTML report writer
```

## Components

### Plugin (`plugin.py`)

Entry point for pytest integration. Implements pytest hooks:

- `pytest_addoption` - registers CLI options
- `pytest_configure` - initializes plugin based on execution mode
- `pytest_sessionstart` - sets up HTTP interception
- `pytest_runtest_setup/teardown` - tracks current test name
- `pytest_runtest_protocol` - safety net to clear current test after each test
- `pytest_sessionfinish` - generates reports
- `pytest_terminal_summary` - prints coverage summary

Two mixins provide shared logic:
- `_InterceptionMixin` — shared HTTP interception logic (used by Single and Worker plugins)
- `_SwaggerLoadMixin` — shared swagger loading logic (used by Single and Master plugins)

Three plugin classes handle different execution modes:
- `CoverageSinglePlugin` - single process execution
- `CoverageMasterPlugin` - xdist master node (aggregates worker data)
- `CoverageWorkerPlugin` - xdist worker node (collects and sends data)

### Adapters (`adapters/`)

HTTP library monkeypatching for request interception.

**RequestsAdapter** (`requests_adapter.py`):
- Patches `requests.Session.request`
- Captures request/response data before returning

**HttpxAdapter** (`httpx_adapter.py`):
- Patches `httpx.Client.request` and `httpx.AsyncClient.request`
- Handles both sync and async HTTP clients

Both adapters:
- Store original methods for restoration
- Call collector with request/response data
- Are thread-safe

### Models (`models.py`)

Data models for HTTP interaction tracking.

```python
@dataclass(frozen=True)
class HTTPRequest:
    method: str
    url: str
    path: str
    host: str
    headers: dict[str, str]
    query_params: dict[str, Any]
    body: Any | None
    content_type: str | None

@dataclass(frozen=True)
class HTTPResponse:
    status_code: int
    headers: dict[str, str]
    content_type: str | None
    body_size: int

@dataclass
class HTTPInteraction:
    request: HTTPRequest
    response: HTTPResponse
    timestamp: datetime
    duration_ms: float
    test_name: str | None
```

### Collector (`collector.py`)

Thread-safe storage for HTTP interactions.

Features:
- Thread-safe via `threading.Lock`
- Tracks current test name per interaction
- Provides `get_data()` for report generation
- Supports `clear()` for reset

### Schemas (`schemas/`)

OpenAPI specification parsing.

**SwaggerParser** (`swagger.py`):
- Parses Swagger 2.0 and OpenAPI 3.x
- Supports JSON and YAML formats
- Loads from local files or URLs
- Extracts endpoints (method + path)
- Extracts base path for prefix stripping

```python
@dataclass
class SwaggerParameter:
    name: str
    location: str        # "path", "query", "header", "body", "formData"
    required: bool = False
    param_type: str | None = None   # "string", "integer", etc.
    schema: dict[str, Any] | None = None

@dataclass
class SwaggerResponse:
    status_code: int
    description: str = ""
    schema: dict[str, Any] | None = None

@dataclass
class SwaggerEndpoint:
    method: str          # GET, POST, etc.
    path: str            # /users/{id}
    operation_id: str | None = None
    summary: str | None = None
    description: str | None = None
    tags: list[str]
    parameters: list[SwaggerParameter]
    responses: list[SwaggerResponse]
    consumes: list[str]
    produces: list[str]

@dataclass
class SwaggerSpec:
    title: str           # defaults to "Unknown API"
    version: str         # defaults to "0.0.0"
    base_path: str = ""
    host: str = ""
    schemes: list[str]
    endpoints: list[SwaggerEndpoint]
    server_urls: list[str]   # OpenAPI 3.x servers
    source: str = ""         # file path or URL
```

### Reporter (`reporter.py`)

Core coverage logic. `CoverageReporter.__init__` accepts `base_url: str | None` for single-origin filtering.

**Path Pattern Matching**:
- Converts OpenAPI paths to regex: `/users/{id}` → `/users/([^/]+)`
- Normalizes actual paths (strips prefixes, removes trailing slashes)
- Matches HTTP requests to OpenAPI endpoints

**Coverage Data Structures**:
```python
@dataclass
class EndpointCoverage:
    method: str
    path: str
    hit_count: int
    response_codes: dict[int, int]  # status_code → count
    test_names: set[str]

@dataclass
class PathCoverage:
    path: str
    methods: list[MethodCoverage]
    # Grouped by path for hierarchical reports
```

**Origin Filtering**:
- `split_by_origin` - separate coverage per origin
- `include_base_urls` (internal) - allowlist of filter strings, used by orchestrator via `api_filters`

### Config (`config/`)

**Settings** (`settings.py`):
- `CoverageSettings` — top-level CLI config
- `SpecConfig` — per-spec config with fields: `name: str`, `api_filters: list[str]`, `swagger_path: str | Path | None`, `swagger_url: str | None`, `strip_prefixes: list[str]`

**MultiSpec loader** (`multi_spec.py`):
- `load_multi_spec_config(path)` — parses YAML/JSON config file

### Orchestrator (`orchestrator.py`)

`MultiSpecOrchestrator` handles multi-spec routing:
- Creates one `CoverageReporter` per `SpecConfig`
- Routes interactions to the correct reporter by matching origin + path prefix (first-match-wins)
- Tracks `unmatched_count` for interactions that match no spec
- Exposes `process_interactions()` and `generate_all_reports()`

### Writers (`writers/`)

Report output in multiple formats.

**JsonWriter** (`json_writer.py`):
- Full structured data with metadata
- Format version for compatibility
- ISO timestamp

**CsvWriter** (`csv_writer.py`):
- Flat table format via Python standard library `csv` module
- Grouped rows (path spans multiple method rows)

**HtmlWriter** (`html_writer.py`):
- Jinja2 template rendering
- CSS styling with color-coded coverage
- Responsive table with rowspan grouping

## Data Flow

1. **Test Execution**
   ```
   pytest runs test → HTTP client makes request
   ```

2. **Interception**
   ```
   Adapter intercepts → extracts request/response → calls Collector
   ```

3. **Collection**
   ```
   Collector stores interaction with test_name and timestamp
   ```

4. **Report Generation**
   ```
   Reporter loads OpenAPI spec
   Reporter processes interactions
   Reporter matches paths to endpoints
   Reporter calculates coverage stats
   ```

5. **Output**
   ```
   Writers generate JSON/CSV/HTML files
   Terminal summary printed
   ```

## pytest-xdist Support

For parallel execution:

```
┌─────────────┐
│   Master    │ ← aggregates data, generates reports
└─────────────┘
       │
   ┌───┴───┐
   ▼       ▼
┌─────┐ ┌─────┐
│ W1  │ │ W2  │ ← workers collect independently
└─────┘ └─────┘
```

- Workers send data via `workeroutput["coverage_data"]`
  - Single-spec mode: plain list of interactions
  - Multi-spec mode: `{"per_spec": {spec_name: [interactions]}, "unmatched_count": int}`
- Master receives via `pytest_testnodedown` hook
- Final aggregation in `pytest_sessionfinish`

## Extension Points

### Adding New HTTP Client Support

1. Create new adapter in `adapters/`
2. Implement the `HttpAdapterProtocol` interface (`adapters/base.py`): instance-based `__init__(self, collector)`, `install(self)`, `uninstall(self)`, `is_installed(self)`
3. Register the class in `ADAPTER_REGISTRY` in `plugin.py`

### Adding New Report Format

1. Create new writer in `writers/`
2. Implement `write(report_data, output_path)` class method
3. Add format to CLI options in `plugin.py`
4. Call writer in `reporter.write_reports()`