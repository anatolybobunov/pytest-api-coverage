# pytest-api-coverage

Pytest plugin for API test coverage analysis. Automatically intercepts HTTP requests during test execution, compares them against Swagger/OpenAPI specifications, and generates detailed coverage reports.

## Features

- **Automatic HTTP interception** — captures requests from `requests` and `httpx` libraries
- **Swagger/OpenAPI support** — works with JSON and YAML specifications (local files or URLs)
- **Multiple report formats** — JSON, CSV, and HTML reports
- **pytest-xdist support** — works with parallel test execution
- **Origin filtering** — filter coverage by base URL or allowlist
- **Split by origin** — generate separate coverage per API origin

## Installation

```bash
pip install pytest-api-coverage
```

## Quick Start

```bash
# Basic usage with local swagger file
pytest tests/ --swagger=swagger.json

# Using swagger URL
pytest tests/ --swagger=https://api.example.com/swagger.json

# With parallel execution
pytest tests/ -n 4 --swagger=swagger.json
```

## How It Works

1. **Interception**: The plugin monkeypatches `requests.Session.request` and `httpx.Client.request` to capture all HTTP requests made during test execution.

2. **Collection**: Each request is recorded with:
   - HTTP method and URL
   - Request path
   - Response status code
   - Test name that made the request

3. **Matching**: After tests complete, recorded requests are matched against endpoints defined in the Swagger/OpenAPI specification using path pattern matching (e.g., `/users/{id}` matches `/users/123`).

4. **Reporting**: Coverage reports are generated showing:
   - Which endpoints were hit and how many times
   - Response codes received
   - Which tests covered each endpoint
   - Overall coverage percentage

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--swagger` | — | **Required.** Path to swagger.json/yaml file or URL to swagger spec |
| `--coverage-output` | `coverage-output` | Output directory for coverage reports |
| `--coverage-format` | `json,csv,html` | Report formats (comma-separated): `json`, `csv`, `html` |
| `--coverage-base-url` | — | Filter coverage to single base URL (origin). Example: `https://api.example.com` |
| `--coverage-include-base-url` | — | Allowlist of base URLs (comma-separated). Example: `https://api.com,https://proxy.com` |
| `--coverage-strip-prefix` | — | Additional path prefixes to strip (comma-separated). Example: `/v1,/api/v2` |
| `--coverage-split-by-origin` | `false` | Generate separate coverage buckets per origin in reports |

## Examples

### Basic Coverage

```bash
pytest tests/ --swagger=api/swagger.yaml
```

Generates reports in `coverage-output/` directory.

### Custom Output Directory

```bash
pytest tests/ --swagger=swagger.json --coverage-output=reports/api-coverage
```

### Only JSON Report

```bash
pytest tests/ --swagger=swagger.json --coverage-format=json
```

### Filter by Base URL

When your tests hit multiple APIs but you only want coverage for one:

```bash
pytest tests/ --swagger=swagger.json --coverage-base-url=https://api.example.com
```

### Multiple Allowed Origins

```bash
pytest tests/ --swagger=swagger.json \
  --coverage-include-base-url=https://api.example.com,https://staging.example.com
```

### Strip Path Prefixes

If your API has versioned paths (`/v1/users`) but swagger defines them without prefix (`/users`):

```bash
pytest tests/ --swagger=swagger.json --coverage-strip-prefix=/v1,/api/v2
```

### Split Coverage by Origin

Generate separate coverage statistics for each API origin:

```bash
pytest tests/ --swagger=swagger.json --coverage-split-by-origin
```

### Parallel Execution with pytest-xdist

```bash
pytest tests/ -n 4 --swagger=swagger.json
```

Coverage data is automatically collected from all workers and aggregated.

## Report Formats

### JSON (`coverage.json`)

Machine-readable format with full details:

```json
{
  "format_version": "1.0",
  "generated_at": "2025-01-15T10:30:00+00:00",
  "swagger_source": "api/swagger.yaml",
  "summary": {
    "total_endpoints": 20,
    "covered_endpoints": 15,
    "coverage_percentage": 75.0,
    "total_requests": 150
  },
  "endpoints": [...]
}
```

### CSV (`coverage.csv`)

Spreadsheet-friendly format with columns:
- Path, Hit Count, Method, Method Count, Response Codes, Covered

### HTML (`coverage.html`)

Visual report with:
- Coverage percentage bar
- Summary statistics
- Color-coded endpoint table (green=covered, gray=once, red=not covered)
- Response code breakdown

## Terminal Output

After test execution, a summary is printed:

```
========================= API Coverage Summary =========================
Endpoints: 15/20 covered (75.0%)
Total HTTP requests: 150

Uncovered endpoints (5):
  - DELETE /users/{id}
  - PATCH /users/{id}
  - POST /admin/reset
  ...
```

## Development

### Install with dev dependencies

```bash
uv sync --group dev
```

### Run tests

```bash
uv run pytest tests/ -v
```

### Lint and format

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

### Type checking

```bash
uv run mypy src/
```

## License

MIT
