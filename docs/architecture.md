# Architecture

## Overview

pytest-api-coverage is a pytest plugin that intercepts HTTP requests during test execution, matches them against a Swagger/OpenAPI specification, and generates coverage reports.

```
┌─────────────────────────────────────────────────────────────────┐
│                         pytest                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    plugin.py                             │    │
│  │  pytest_configure → pytest_sessionstart → pytest_runtest │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│         ┌────────────────────┼────────────────────┐             │
│         ▼                    ▼                    ▼             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │
│  │  Adapters   │     │  Collector  │     │   Schemas   │       │
│  │  requests   │────▶│  thread-    │     │  swagger    │       │
│  │  httpx      │     │  safe       │     │  parser     │       │
│  └─────────────┘     └─────────────┘     └─────────────┘       │
│                              │                    │             │
│                              ▼                    ▼             │
│                       ┌─────────────────────────────┐           │
│                       │        Reporter             │           │
│                       │  path matching + coverage   │           │
│                       └─────────────────────────────┘           │
│                                     │                           │
│                    ┌────────────────┼────────────────┐          │
│                    ▼                ▼                ▼          │
│             ┌───────────┐    ┌───────────┐    ┌───────────┐    │
│             │   JSON    │    │    CSV    │    │   HTML    │    │
│             │  Writer   │    │  Writer   │    │  Writer   │    │
│             └───────────┘    └───────────┘    └───────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Module Structure

```
src/pytest_api_coverage/
├── __init__.py
├── plugin.py           # Pytest plugin entry point
├── collector.py        # Thread-safe request collection
├── reporter.py         # Coverage matching and reporting
├── models.py           # Data models
├── adapters/
│   ├── __init__.py
│   ├── requests_adapter.py   # requests library interception
│   └── httpx_adapter.py      # httpx library interception
├── config/
│   ├── __init__.py
│   └── settings.py     # Configuration settings
├── schemas/
│   ├── __init__.py
│   └── swagger.py      # Swagger/OpenAPI parser
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
- `pytest_sessionfinish` - generates reports
- `pytest_terminal_summary` - prints coverage summary

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

### Collector (`collector.py`)

Thread-safe storage for HTTP interactions.

```python
@dataclass
class HttpInteraction:
    request: dict    # method, url, path, headers
    response: dict   # status_code, headers
    test_name: str   # pytest node ID
    timestamp: float
```

Features:
- Thread-safe via `threading.Lock`
- Tracks current test name per interaction
- Provides `get_data()` for report generation
- Supports `clear()` for reset

### Schemas (`schemas/`)

Swagger/OpenAPI specification parsing.

**SwaggerParser** (`swagger.py`):
- Parses Swagger 2.0 and OpenAPI 3.x
- Supports JSON and YAML formats
- Loads from local files or URLs
- Extracts endpoints (method + path)
- Extracts base path for prefix stripping

```python
@dataclass
class SwaggerEndpoint:
    method: str  # GET, POST, etc.
    path: str    # /users/{id}

@dataclass
class SwaggerSpec:
    endpoints: list[SwaggerEndpoint]
    base_path: str | None
    source: str  # file path or URL
```

### Reporter (`reporter.py`)

Core coverage logic.

**Path Pattern Matching**:
- Converts swagger paths to regex: `/users/{id}` → `/users/([^/]+)`
- Normalizes actual paths (strips prefixes, removes trailing slashes)
- Matches HTTP requests to swagger endpoints

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
- `base_url` - single origin filter
- `include_base_urls` - allowlist of origins
- `split_by_origin` - separate coverage per origin

### Writers (`writers/`)

Report output in multiple formats.

**JsonWriter** (`json_writer.py`):
- Full structured data with metadata
- Format version for compatibility
- ISO timestamp

**CsvWriter** (`csv_writer.py`):
- Flat table format via pandas
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
   Reporter loads Swagger spec
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
- Master receives via `pytest_testnodedown` hook
- Final aggregation in `pytest_sessionfinish`

## Extension Points

### Adding New HTTP Client Support

1. Create new adapter in `adapters/`
2. Implement `install(collector)` and `uninstall()` class methods
3. Register in `plugin.py` setup/teardown

### Adding New Report Format

1. Create new writer in `writers/`
2. Implement `write(report_data, output_path)` class method
3. Add format to CLI options in `plugin.py`
4. Call writer in `reporter.write_reports()`